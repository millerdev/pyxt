from testil import eq

from .. import argwrap as mod
from ...tests.util import async_test, do_command, FakeEditor, gentest


def test_argwrap():
    @gentest
    @async_test
    async def test(text, expect, sel2, sel3, sel1=(1, 1), filename="test.py"):
        editor = FakeEditor(filename, text=text)
        editor.selection = sel1
        await do_command("argwrap", editor)
        eq(await editor.get_text(), expect)
        eq(await editor.selection(), sel2)
        await do_command("argwrap", editor)
        eq(await editor.get_text(), text)
        eq(await editor.selection(), sel3)

    yield test(
        """
        def f(a, b):
            pass
        """,
        """
        def f(
            a,
            b,
        ):
            pass
        """,
        sel2=(1, 56),
        sel3=(1, 21),
    )
    yield test(
        """
        def func(arg, f(a, b), (1, 2), [3, 4], {5, 6}):
            pass
        """,
        """
        def func(
            arg,
            f(a, b),
            (1, 2),
            [3, 4],
            {5, 6},
        ):
            pass
        """,
        sel2=(1, 127),
        sel3=(1, 56),
    )


def test_should_wrap():
    @gentest
    def test(text, rng, expect, eol="\n"):
        result = mod.should_wrap(text, rng, eol)
        eq(result, expect, text)

    yield test("def f(a): pass", (0, 0), True)
    yield test("def f(a): pass", (6, 7), True)
    yield test("def f(a): pass\n", (0, 15), True)
    yield test("def f(\n    a,\n): pass", (5, 7), True)
    yield test("def f(\n    a,\n): pass", (5, 8), False)
    yield test("def f(\n    a,\n): pass", (0, 21), False)


def test_wrap():
    @gentest
    def test(
        parts,
        expect,
        eol="\n",
        insert_spaces=True,
        tab_size=4,
        trailing_comma=True,
    ):
        text = mod.wrap(parts, eol, insert_spaces, tab_size, trailing_comma)
        eq(text, expect)

    yield test(["def f(", "a", "): pass"], "def f(\n    a,\n): pass")
    yield test(
        ["def f(", "a,", "b", "): pass"],
        "def f(\n    a,\n    b,\n): pass",
    )
    yield test(
        ["def f(", "a,", "b,", "): pass"],
        "def f(\n    a,\n    b,\n): pass",
    )
    yield test(["  def f(", "a", "): pass"], "  def f(\n      a,\n  ): pass")
    yield test(
        ["  def f(", "a", "): pass"],
        "  def f(\n    a,\n  ): pass",
        tab_size=2,
    )
    yield test(
        ["\tdef f(", "a", "): pass"],
        "\tdef f(\n\t\ta,\n\t): pass",
        insert_spaces=False,
    )
    yield test(
        ["def f(", "a", "): pass"],
        "def f(\n    a\n): pass",
        trailing_comma=False,
    )


def test_unwrap():
    @gentest
    def test(lines, expect, **kw):
        text = mod.unwrap(lines, **kw)
        eq(text, expect)

    yield test(["def f(", "    a", "): pass"], "def f(a): pass")
    yield test(["def f(", "    a,", "): pass"], "def f(a): pass")
    yield test(["def f(", "    a,", "    b", "): pass"], "def f(a, b): pass")
    yield test(["def f(", "    a,", "    b,", "): pass"], "def f(a, b): pass")
    yield test(["x = [", "    a", "]"], "x = [a]")
    yield test(["x = [", "    a,", "]"], "x = [a]")
    yield test(["x = {", "    a", "}"], "x = {a}")
    yield test(["x = {", "    a,", "}"], "x = {a}")
    yield test(["  def f(", "    a", "  ): pass"], "  def f(a): pass")


def test_split_line():
    @gentest
    def test(text, index, expect, expect_range):
        parts, rng = mod.split_line(text, index)
        eq(parts, expect)
        eq(rng, expect_range)

    yield test("def f(a): pass", 0, ["def f(", "a", "): pass"], (0, 14))
    yield test("def f(\n    a,\n): pass", 0, [], (0, 6))
    yield test("def f(\n    a,\n): pass", 5, [], (0, 6))
    yield test("def f(\n    a,\n): pass", 7, [], (7, 13))
    yield test("def f(\n    a,\n): pass", 8, [], (7, 13))
    yield test("def f(\n    f(a),\n): pass", 8, ["    f(", "a", "),"], (7, 16))
    yield test("return a, b,", 0, [], (0, 12))
    yield test("return f(a, b, c),", 0, ["return f(", "a,", "b,", "c", "),"], (0, 18))
    yield test("return f((a, b, c)),", 0, ["return f(", "(a, b, c)", "),"], (0, 20))
    yield test("return f([a, b, c]),", 0, ["return f(", "[a, b, c]", "),"], (0, 20))
    yield test("return f({a, b, c}),", 0, ["return f(", "{a, b, c}", "),"], (0, 20))
    yield test("return f([a, ']', c]),", 0, ["return f(", "[a, ']', c]", "),"], (0, 22))
    yield test("def f(a, (1, 2)): pass", 0,
        ["def f(", "a,", "(1, 2)", "): pass"], (0, 22))
    yield test("'(...)'", 0, [], (0, 7))
    yield test("('\\'')", 0, ["(", "'\\''", ")"], (0, 6))
    yield test("('\\\\')", 0, ["(", "'\\\\'", ")"], (0, 6))
    yield test("('\\\\\\'')", 0, ["(", "'\\\\\\''", ")"], (0, 8))
    yield test("""
        def f(a, b):
            pass
    """, 1, ["        def f(", "a,", "b", "):"], (1, 21))

    yield test("), (arg)", 0, [], (0, 8))
    yield test("), (arg)", 1, ["), (", "arg", ")"], (0, 8))
    yield test("(a)), (arg)", 0, ["(", "a", ")), (arg)"], (0, 11))
    yield test("(a)), (arg)", 1, ["(", "a", ")), (arg)"], (0, 11))


def test_split_lines():
    @gentest
    def test(text, rng, expect, eol="\n"):
        lines = list(mod.split_lines(text, rng, eol))
        eq(lines, expect)

    yield test("def f(\n    a,\n): pass", (4, 9), ["f(", "  "])
    yield test("def f(\n    a,\n): pass", (0, 14), ["def f(", "    a,\n"])
    yield test("def f(\n    a,\n): pass", (0, 21), [
        "def f(",
        "    a,",
        "): pass",
    ])
    yield test("def f(\n    a,\n): pass\n", (0, 22), [
        "def f(",
        "    a,",
        "): pass\n",
    ])
    yield test("x = [\n    a\n]\n", (0, 14), ["x = [", "    a", "]\n"])
    yield test("x = {\n    a\n}\n", (0, 14), ["x = {", "    a", "}\n"])
    yield test("x = [\n    a,\n]\n", (0, 14), ["x = [", "    a,", "]"])
    yield test("x = {\n    a,\n}\n", (0, 14), ["x = {", "    a,", "}"])
