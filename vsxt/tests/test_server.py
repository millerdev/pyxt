from contextlib import contextmanager

from nose.tools.nontrivial import nottest
from testil import eq, replattr

from .. import command
from .. import server as mod
from ..parser import Choice, CommandParser
from ..results import error, result
from ..tests.util import async_test


def test_do_command():
    @async_test
    async def test(input_value, expected_result):
        server = object()
        with test_command():
            res = await mod.do_command(server, [input_value])
            eq(res, expected_result)

    yield test, "", result(["cmd"], "", offset=0)
    yield test, "cm", error("Unknown command: 'cm'")
    yield test, "cmd ", result(value="a")
    yield test, "cmd a", result(value="a")


def test_get_completions():
    @async_test
    async def test(input_value, expected_result):
        server = object()
        with test_command():
            res = await mod.get_completions(server, [input_value])
            eq(res, expected_result)

    yield test, "cm", result(["cmd"], "cm", offset=0)
    yield test, "cmd", result(["a", "b"], "cmd ", offset=4)
    yield test, "cmd ", result(["a", "b"], "cmd ", offset=4)
    yield test, "cmd a", result(["a"], "cmd a", offset=4)


def test_parse_command():
    def test(input_value, expected_args, expected_offset, found=True):
        with test_command():
            command, args, offset = mod.parse_command(input_value)
            if found:
                assert command is not None, f"command not found: {input_value}"
            else:
                assert command is None, f"unexpected command: {command}"
            eq(args, expected_args)
            eq(offset, expected_offset)

    yield test, "cm", "cm", 0, False
    yield test, "c md", "c", 0, False
    yield test, "cmd", "", 4
    yield test, "cmd ", "", 4
    yield test, "cmd file", "file", 4
    yield test, "cmd a b", "a b", 4


@nottest
@contextmanager
def test_command():
    with replattr(command, "REGISTRY", {}):
        @command.command(parser=CommandParser(Choice("a b", name="value")))
        async def cmd(editor, args):
            return result(value=args.value)
        yield
