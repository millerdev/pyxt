from contextlib import contextmanager

from nose.tools.nontrivial import nottest
from testil import eq, replattr

from .. import command
from .. import server as mod
from ..parser import Choice, String
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
    yield test, "cmd too many arguments", error(
        "invalid arguments: too many arguments\n"
        "'too' does not match any of: a, b"
    )


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
                String("arg", default="val"),
                Choice("yes no"),
                has_placeholder_item=True,
            )
            async def prog(editor, args):
                return result(value=args.arg)

            res = await mod.get_completions(server, [input_value])
            eq(res, expected_result)

    yield test("prog", result([
        item("prog ", 0, description="val yes"),
    ], "prog "))
    yield test("prog ", result([
        item("prog ", 0, description="val yes"),
    ], "prog "))
    yield test("prog  ", result([
        item("prog val", 0, description="yes"),
        item("yes", 6, is_completion=True),
        item("no", 6, is_completion=True),
    ], "prog  "))
    yield test("prog ' ", result([
        item("prog ' '", 0, description="yes"),
    ], "prog ' "))
    yield test("prog ' '", result([
        item("prog ' '", 0, description="yes"),
        item("yes", 9, is_completion=True),
        item("no", 9, is_completion=True),
    ], "prog ' '"))
    yield test("prog ' ' ", result([
        item("prog ' '", 0, description="yes"),
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


def test_command_completions():
    commands = [x["label"] for x in mod.command_completions()["items"]]
    assert "hello " not in commands, commands
    eq(commands, sorted(commands))


def test_load_user_script():
    from os.path import abspath, dirname, join
    with test_command("zzz"):
        root = dirname(dirname(abspath(mod.__file__)))
        path = join(root, "testfiles", "hello.py")
        mod.load_user_script([path])
        commands = [x["label"] for x in mod.command_completions()["items"]]
        assert "hello " in commands, commands
        eq(commands, sorted(commands))


@nottest
@contextmanager
def test_command(name="cmd"):
    with replattr(command, "REGISTRY", {}):
        @command.command(
            Choice("a b", name="value"),
            name=name,
            has_placeholder_item=False,
        )
        async def cmd(editor, args):
            return result(value=args.value)
        yield


def item(label, offset, **kw):
    return {"label": label, "offset": offset, **kw}
