import os
from os.path import join

from testil import eq, tempdir

from ...tests.util import async_test, do_command, FakeEditor, gentest


def test_rename():
    @gentest
    @async_test
    async def test(new_name, expected_path, old_path="/path/to/file.py"):
        editor = FakeEditor(old_path, text="...")
        await do_command(f"rename {new_name}", editor)
        new_path = await editor.file_path
        eq(new_path, expected_path)

    yield test("file.md", "/path/to/file.md")
    yield test("../file.md", "/path/to/../file.md")
    yield test("sub/", "/path/to/sub/file.py")
    yield test("/somewhere/else.md", "/somewhere/else.md")
    yield test("/somewhere/", "/somewhere/file.py")
    with tempdir() as tmp:
        os.mkdir(join(tmp, "somewhere"))
        yield test(join(tmp, "somewhere"), join(tmp, "somewhere/file.py"))
