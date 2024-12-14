from testil import eq

from ...tests.util import (
    async_test,
    do_command,
    FakeEditor,
    gentest,
    yield_test,
)


@yield_test
def test_replace_command():
    @gentest
    @async_test
    async def test(command, selection=(0, 0), expect=None):
        if expect is None:
            expect = TEXT
        editor = FakeEditor(__file__, text=TEXT)
        editor.selection = selection
        await do_command(command, editor)
        eq(await editor.get_text(), expect)

    yield test("replace '/'.' all", expect=TEXT.replace("/", "."))
    yield test("replace '/'.'", (1, 17), expect=TEXT.replace("/", ".", 2))
    yield test("replace '/'.' sel", (1, 17), expect=TEXT.replace("/", ".", 2))
    yield test("replace /t/x/i all", expect=TEXT.replace("t", "x").replace("T", "x"))
    yield test('replace "."" all literal', expect=TEXT.replace(".", ""))
    yield test("replace /..// all word",
               expect=TEXT.replace(".py", ".").replace("TO", ""))


TEXT = """
pyxt/cmd/replace.py

path/TO/file
"""
