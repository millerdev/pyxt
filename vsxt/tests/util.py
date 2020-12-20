import asyncio
from dataclasses import dataclass
from functools import wraps
from os.path import dirname

from nose.tools import nottest
from testil import replattr

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
    if editor is None:
        editor = FakeEditor()
    srv = object()
    with replattr(server, "Editor", lambda srv: editor):
        return await server.do_command(srv, [input_value])


@dataclass
class FakeEditor:
    _file_path: str = None
    _project_path: str = None
    _selection: str = ""

    @property
    async def file_path(self):
        return self._file_path

    @property
    async def project_path(self):
        return self._project_path

    @property
    async def dirname(self):
        filepath = await self.file_path
        return dirname(filepath) if filepath else None

    @property
    async def selection(self):
        return self._selection
