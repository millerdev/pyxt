import os
from os.path import join

from testil import eq, tempdir

from ...tests.util import (
    async_test,
    do_command,
    FakeEditor,
    gentest,
    get_completions,
    yield_test,
)


@yield_test
def test_rename():
    @gentest
    @async_test
    async def test(new_name, expected_path):
        editor = FakeEditor("/path/to/file.py", text="...")
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


@yield_test
def test_rename_completions():
    with tempdir() as tmp:
        os.mkdir(join(tmp, "dir"))
        with open(join(tmp, "file.py"), "w"):
            pass

        @gentest
        @async_test
        async def test(cmd, label="", items=()):
            filepath = join(tmp, "file.py")
            editor = FakeEditor(filepath, text="...")
            result = await get_completions(cmd, editor)
            items = list(items)
            items.insert(0, {
                "label": label or cmd,
                "description": filepath + "  ",
                "offset": 0,
            })
            eq(result["items"], items)
            eq(result["value"], cmd)

        yield test("rename ", label="rename", items=[
            {'label': 'dir/', 'offset': 7, 'is_completion': True},
            {'label': 'file.py ', 'offset': 7, 'is_completion': True},
        ])
