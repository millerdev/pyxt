from testil import eq, Regex

from ...process import ProcessError
from ...tests.util import async_test, do_command, FakeEditor, gentest


def test_doc():
    @gentest
    @async_test
    async def test(code, output, command="python"):
        editor = FakeEditor(text=code)
        result = await do_command(command, editor)
        eq(result["items"], [{"label": output, "copy": True}])
        assert result.get("filter_results"), result

    yield test("1 + 1", "2")
    yield test("print(1 + 1)", "2")
    yield test("  2 + 2", "4")
    yield test("  print('hi')\n  2 + 2\n", "hi\n4")
    yield test(
        """
        def f(x):
            return x
        """,
        "no output"
    )
    yield test(
        """
        (1
            + 2)
        """,
        "3"
    )
    yield test(
        """
        (1
            + 2)
        # comment
        """,
        "3"
    )
    yield test(
        """
        x = 4
        y = 1;x + y
        """,
        "5"
    )
    yield test("1 + 1", "4", "python   -c 'print(4)'")


@async_test
async def test_syntax_error():
    editor = FakeEditor(text='print "not with python 3"')
    try:
        await do_command("python", editor)
    except ProcessError as err:
        eq(str(err), Regex("SyntaxError"))
