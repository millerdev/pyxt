from testil import eq

from .. import command
from .. import history
from .. import server as mod
from ..parser import Choice, String
from ..results import error, result
from ..tests.util import async_test, fake_history, gentest, test_command


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


def test_do_command_with_history():
    @gentest
    @async_test
    async def test(input_values, history_cache, client_calls):
        server = {"calls": []}
        with test_command(String("value")), fake_history():
            for value in input_values:
                await mod.do_command(server, [value])
            eq(history.cache, history_cache)
            eq(server["calls"], client_calls)

    yield test(["cmd"], {}, [])
    yield test(["cmd a"], {"cmd": ["a"]}, ["history.update('cmd', 'a')"])
    yield test(["cmd a", "cmd b"], {"cmd": ["b", "a"]}, [
        "history.update('cmd', 'a')",
        "history.update('cmd', 'b')",
    ])
    yield test(["cmd a", "cmd b", "cmd a"], {"cmd": ["a", "b"]}, [
        "history.update('cmd', 'a')",
        "history.update('cmd', 'b')",
        "history.update('cmd', 'a')",
    ])
    yield test([f"cmd {n}" for n in range(15)], {
        "cmd": [str(n) for n in reversed(range(5, 15))]
    }, [
        "history.update('cmd', '0')",
        "history.update('cmd', '1')",
        "history.update('cmd', '2')",
        "history.update('cmd', '3')",
        "history.update('cmd', '4')",
        "history.update('cmd', '5')",
        "history.update('cmd', '6')",
        "history.update('cmd', '7')",
        "history.update('cmd', '8')",
        "history.update('cmd', '9')",
        "history.update('cmd', '10')",
        "history.update('cmd', '11')",
        "history.update('cmd', '12')",
        "history.update('cmd', '13')",
        "history.update('cmd', '14')",
    ])
    yield test(["cmd error"], {}, [])


def test_get_completions():
    @async_test
    async def test(input_value, expected_result):
        server = object()
        with test_command():
            @command.command(String("value"))
            def count(editor, args):
                return result(value=args.value)
            res = await mod.get_completions(server, [input_value])
            eq(res, expected_result)

    yield test, "cm", result([item("cmd ", 0, is_completion=True)], "cm")
    yield test, "cmd", result([item("a", 4), item("b", 4)], "cmd ", placeholder="cmd a")
    yield test, "cmd ", result([item("a", 4), item("b", 4)], "cmd ", placeholder="cmd a")
    yield test, "cmd a", result([item("a", 4)], "cmd a")
    yield test, "c", result([
        item("cmd ", 0, is_completion=True),
        item("count ", 0, is_completion=True),
    ], "c")


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
        item("prog", 0, description="val yes"),
    ], "prog ", placeholder="val yes"))
    yield test("prog ", result([
        item("prog", 0, description="val yes"),
    ], "prog ", placeholder="val yes"))
    yield test("prog  ", result([
        item("prog val", 0, description="yes"),
        item("yes", 6),
        item("no", 6),
    ], "prog  ", placeholder="yes"))
    yield test("prog ' ", result([
        item("prog ' '", 0, description="yes"),
    ], "prog ' ", placeholder="yes"))
    yield test("prog ' '", result([
        item("prog ' '", 0, description="yes"),
        item("yes", 9),
        item("no", 9),
    ], "prog ' '", placeholder="yes"))
    yield test("prog ' ' ", result([
        item("prog ' '", 0, description="yes"),
        item("yes", 9),
        item("no", 9),
    ], "prog ' ' ", placeholder="yes"))
    yield test("prog ' ' y", result([
        item("prog ' ' yes", 0, description=""),
        item("yes", 9),
    ], "prog ' ' y"))


def test_get_completions_with_history():
    @gentest
    @async_test
    async def test(input_value, result, pre_cache=None, calls=(), cache=None):
        server = {"calls": []}
        if calls:
            for call, value in calls.items():
                server[call] = value
        with test_command(with_history=True), fake_history(dict(pre_cache or {})):
            res = await mod.get_completions(server, [input_value])
            eq(res, result)
            eq(server["calls"], list(calls))
            eq(history.cache, cache or pre_cache)

    def res(items=()):
        items = list(items) + [item("a", offset=4), item("b", offset=4)]
        return result(items, value="cmd ", placeholder="cmd a")

    yield test("cmd", res(), calls={"history.get('cmd',)": []}, cache={"cmd": []})
    yield test("cmd", res([
        item("cmd a", 0),
        item("cmd b", 0),
    ]), {"cmd": ["a", "b"]})
    yield test(
        "cmd",
        res([item("cmd b", 0)]),
        calls={"history.get('cmd',)": ["b"]}, cache={"cmd": ["b"]},
    )
    yield test("cmd a", result([
        item("cmd a", 0),
        item("a", 4),
    ], value="cmd a"), {"cmd": ["a", "b"]})


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
    with test_command(name="zzz"):
        root = dirname(dirname(abspath(mod.__file__)))
        path = join(root, "testfiles", "hello.py")
        mod.load_user_script([path])
        commands = [x["label"] for x in mod.command_completions()["items"]]
        assert "hello " in commands, commands
        eq(commands, sorted(commands))


def item(label, offset, **kw):
    return {"label": label, "offset": offset, **kw}
