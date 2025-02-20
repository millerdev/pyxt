import asyncio
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutine
from os.path import dirname
from unittest.mock import patch

from .. import command
from .. import history
from .. import jsproxy
from .. import server
from ..parser import Choice
from ..results import error, result


def async_test(func):
    @wraps(func)
    def test(*args, **kw):
        return asyncio.run(func(*args, **kw))
    return test


async_test.__test__ = False


def await_coroutine(value):
    """HACK synchronously await coroutine"""
    return asyncio.run(value)


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
    with (
        patch.object(server, "Editor", lambda srv: editor),
        patch.object(server, "error", reraise),
        patch.object(history, "update_history", do_not_update_history),
    ):
        return await server.do_command(srv, [input_value])


async def get_completions(input_value, editor=None):
    async def no_history(server, command_name, argstr=""):
        return []
    if editor is None:
        editor = FakeEditor()
    srv = object()
    with (
        patch.object(server, "Editor", lambda srv: editor),
        patch.object(server, "get_history", no_history),
    ):
        return await server.get_completions(srv, [input_value])


@contextmanager
def test_command(*args, name="cmd", with_history=False):
    async def no_history(server, command_name, argstr=""):
        return []
    if not args:
        args = Choice("a b", name="value"),
    if with_history:
        history_patch = nullcontext()
    else:
        history_patch = patch.object(server, "get_history", no_history)
    with patch.object(command, "REGISTRY", {}), history_patch:
        @command.command(name=name, has_placeholder_item=False, *args)
        async def cmd(editor, args):
            if args.value == "error":
                return error("error")
            return result(value=args.value)
        yield


test_command.__test__ = False


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

    with (
        patch.object(history, "async_do", async_do),
        patch.object(history, "cache", cache or {}),
        patch.object(jsproxy, "_get", get),
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
    _eol: str = "\n"
    _insert_spaces: bool = True
    _tab_size: int = 4

    file_path = async_property("_file_path")
    project_path = async_property("_project_path")
    ag_path = async_property("_ag_path")
    python_path = async_property("_python_path")
    eol = async_property("_eol")
    insert_spaces = async_property("_insert_spaces")
    tab_size = async_property("_tab_size")

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

    async def selections(self, values=None):
        if values is None:
            return [self._selected_range]
        raise NotImplementedError

    async def get_text(self, rng=None):
        if iscoroutine(rng):
            rng = await rng
        if rng is None:
            return self.text
        start, end = rng
        return self.text[start:end]

    async def get_texts(self, ranges):
        return await asyncio.gather(*[self.get_text(rng) for rng in ranges])

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
        self.selection = (start, start + len(value)) if select else (end, end)

    async def set_texts(self, values, ranges, select=True):
        if len(values) != len(ranges):
            raise ValueError(
                f"values/ranges mismatch: {len(values)} != {len(ranges)}")
        if len(values) > 1:
            raise NotImplementedError
        await self.set_text(values[0], ranges[0], select)

    async def rename(self, path, overwrite=False):
        self._file_path = path


class Error(Exception):
    pass


def yield_test(testfunc):
    """Adapt yield tests to pytest

    Works with tests that have exactly as many literal yield
    statements (at the beginning of a line) as there are tests.
    """
    # HACK adapt yield tests to pytest
    # TODO rewrite yield tests with pytest.mark.parametrize
    import pytest
    import re
    from inspect import getsource
    from unmagic import fixture

    @fixture(scope="module")
    def yield_tester():
        tests = testfunc()
        yield tests
        teardown_generator(tests)

    def teardown_generator(tests):
        name = testfunc.__name__
        print(f"{name} executed {yield_count} yield tests")
        with pytest.raises(StopIteration):
            value = next(tests)  # should raise
            print(f"unexpected yield value for {name}:", repr(value))

    YIELD = re.compile(r"^\s+yield\b", re.MULTILINE)
    yield_count = sum(1 for x in YIELD.finditer(getsource(testfunc)))

    @pytest.mark.parametrize("i", range(yield_count))
    def run_test(i):
        tests = yield_tester()
        test, *args = next(tests)
        name = getattr(test, "__name__", "test")
        print(f"{name}{tuple(args)}")
        test(*args)
        if i + 1 >= yield_count:
            teardown_generator(tests)

    run_test.__name__ = testfunc.__name__
    return run_test
