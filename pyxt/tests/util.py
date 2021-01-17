import asyncio
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutine
from os.path import dirname

from nose.tools import nottest
from testil import replattr

from .. import editor
from .. import history
from .. import server


@nottest
def async_test(func):
    @wraps(func)
    def test(*args, **kw):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(func(*args, **kw))
        finally:
            loop.close()
    return test


def await_coroutine(value):
    """HACK synchronously await coroutine"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(value)
    finally:
        loop.close()


def gentest(test):
    """A decorator for nose generator tests

    Usage:

        def generator_test():
            @gentest
            def test(a, b=None, c=4):
                ...
            yield test(1)
            yield test(1, 2)
            yield test(1, c=3)

    WARNING do not use this to decorate test functions outside of a generator
    test. It will cause the test to appear to pass without actually running it.
    """
    @wraps(test)
    def assemble_test_args(*args, **kw):
        @wraps(test)
        def run_test_with(*ignore):
            rval = test(*args, **kw)
            assert rval is None, "test returned unexpected value: %r" % (rval,)
        display_args = args
        if kw:
            visible_kw = {k: v for k, v in kw.items() if not k.startswith("_")}
            display_args += (KeywordArgs(visible_kw),)
        return (run_test_with,) + display_args

    def make_partial(assembler):
        @wraps(test)
        def partial(*args, **kw):
            @wraps(test)
            def assemble(*more_args, **more_kw):
                new_kw = dict(kw, **more_kw)
                return assembler(*(args + more_args), **new_kw)
            assemble.test = test
            assemble.partial = make_partial(assemble)
            return assemble
        return partial

    assemble_test_args.test = test
    assemble_test_args.partial = make_partial(assemble_test_args)
    return assemble_test_args


class KeywordArgs:
    def __init__(self, kw):
        self.kw = kw

    def __repr__(self):
        return ", ".join("%s=%r" % kv for kv in sorted(self.kw.items()))


async def do_command(input_value, editor=None):
    def reraise(message):
        if sys.exc_info()[1] is not None:
            raise sys.exc_info()[1]
        raise Error(message)

    def do_not_update_history(server, input_value, command):
        pass

    if editor is None:
        editor = FakeEditor()
    srv = object()
    with replattr(
        (server, "Editor", lambda srv: editor),
        (server, "error", reraise),
        (history, "update_history", do_not_update_history),
    ):
        return await server.do_command(srv, [input_value])


async def get_completions(input_value, editor=None):
    async def no_history(server, command, argstr):
        return []
    if editor is None:
        editor = FakeEditor()
    srv = object()
    with replattr(
        (server, "Editor", lambda srv: editor),
        (server, "get_history", no_history),
    ):
        return await server.get_completions(srv, [input_value])


@contextmanager
def fake_history(cache=None):
    def async_do(proxy):
        path = str(proxy)
        server, params = proxy._resolve()
        server["calls"].append(path)

    async def get(proxy):
        path = str(proxy)
        server, params = proxy._resolve()
        server["calls"].append(path)
        return server.get(path, path)

    with replattr(
        (history, "async_do", async_do),
        (history, "cache", cache or {}),
        (history, "get", get),
        (editor, "get", get),
    ):
        yield


class async_property:
    def __init__(self, name):
        self.name = name

    async def __get__(self, owner, type=None):
        if owner is None:
            return self
        return getattr(owner, self.name)

    def __set__(self, owner, value):
        return setattr(owner, self.name, value)


@dataclass
class FakeEditor:
    _file_path: str = None
    _project_path: str = None
    _selected_range: tuple = (0, 0)
    text: str = ""
    _ag_path: str = "ag"
    _python_path: str = "python"

    file_path = async_property("_file_path")
    project_path = async_property("_project_path")
    ag_path = async_property("_ag_path")
    python_path = async_property("_python_path")

    @property
    async def dirname(self):
        filepath = await self.file_path
        return dirname(filepath) if filepath else None

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if isinstance(value, str):
            self.text = value
            self._selected_range = (0, len(value))
        else:
            self._selected_range = tuple(value)

    async def _selection(self, value=None):
        if value is None:
            return self._selected_range
        self.selection = value

    async def get_text(self, rng=None):
        if iscoroutine(rng):
            rng = await rng
        if rng is None:
            return self.text
        start, end = rng
        return self.text[start:end]

    async def set_text(self, value, rng=None, select=True):
        if rng is None:
            start = 0
            end = len(self.text)
        else:
            if iscoroutine(rng):
                rng = await rng
            start, end = rng
        self.text = "".join([
            self.text[:start],
            value,
            self.text[end:],
        ])
        self._selection = (start, len(value)) if select else (end, end)


class Error(Exception):
    pass
