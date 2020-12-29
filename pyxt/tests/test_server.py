from contextlib import contextmanager

from nose.tools.nontrivial import nottest
from testil import eq, replattr

from .. import command
from .. import server as mod
from ..parser import Choice, CommandParser, String
from ..results import error, result
from ..tests.util import async_test, gentest


def test_do_command():
    @async_test
    async def test(input_value, expected_result):
        server = object()
        with test_command():
            res = await mod.do_command(server, [input_value])
            eq(res, expected_result)

    yield test, "", result([item("cmd ", 0, is_completion=True)], "")
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

    yield test, "cm", result([item("cmd ", 0, is_completion=True)], "cm")
    yield test, "cmd", result([item("a", 4), item("b", 4)], "cmd ")
    yield test, "cmd ", result([item("a", 4), item("b", 4)], "cmd ")
    yield test, "cmd a", result([item("a", 4)], "cmd a")


def test_get_completions_with_placeholder_item():
    server = object()

    @gentest
    @async_test
    async def test(input_value, expected_result):
        with test_command():
            @command.command(
                parser=CommandParser(String("arg"), Choice("yes no")),
                has_placeholder_item=True,
            )
            async def prog(editor, args):
                return result(value=args.arg)

            res = await mod.get_completions(server, [input_value])
            eq(res, expected_result)

    yield test("prog", result([
        item("prog ", 0, description="arg yes"),
    ], "prog "))
    yield test("prog ", result([
        item("prog ", 0, description="arg yes"),
    ], "prog "))
    yield test("prog ' ", result([
        item("prog ' '", 0, description="yes"),
    ], "prog ' "))
    yield test("prog ' '", result([
        item("prog ' '", 0, description="yes"),
        item("yes", 9, is_completion=True),
        item("no", 9, is_completion=True),
    ], "prog ' '"))
    yield test("prog ' ' ", result([
        item("prog ' ' ", 0, description="yes"),
        item("yes", 9, is_completion=True),
        item("no", 9, is_completion=True),
    ], "prog ' ' "))
    yield test("prog ' ' y", result([
        item("prog ' ' yes", 0, description=""),
        item("yes", 9, is_completion=True),
    ], "prog ' ' y"))


def test_parse_command():
    def test(input_value, expected_args, found=True):
        with test_command():
            command, args = mod.parse_command(input_value)
            if found:
                assert command is not None, f"command not found: {input_value}"
            else:
                assert command is None, f"unexpected command: {command}"
            eq(args, expected_args)

    yield test, "cm", "cm", False
    yield test, "c md", "c", False
    yield test, "cmd", ""
    yield test, "cmd ", ""
    yield test, "cmd file", "file"
    yield test, "cmd a b", "a b"


@nottest
@contextmanager
def test_command():
    with replattr(command, "REGISTRY", {}):
        @command.command(parser=CommandParser(Choice("a b", name="value")))
        async def cmd(editor, args):
            return result(value=args.value)
        yield


def item(label, offset, **kw):
    return {"label": label, "offset": offset, **kw}