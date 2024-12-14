from contextlib import contextmanager
from os.path import exists, join
from pathlib import Path

from testil import eq, tempdir

from .. import openfile as mod
from ...results import result
from ...tests.util import FakeEditor, async_test, do_command, yield_test


@yield_test
def test_open_file():
    with fake_editor() as editor:
        @async_test
        async def test(cmdstr, expect):
            result = await do_command(cmdstr, editor)
            base = await editor.dirname
            if isinstance(expect, str):
                eq(result["type"], "success", result)
                eq(normalize_path(result["value"], base), expect)
            else:
                if "placeholder" in result:
                    result["placeholder"] = result["placeholder"].replace(base, "/base")
                normalize_paths(result["items"], base)
                eq(result, expect)

        yield test, "open file.txt", "/file.txt"
        yield test, "open dir/file.txt", "/dir/file.txt"
        yield test, "open ../file.txt", "/../file.txt"
        yield test, "open ", result([
            {"label": "dir/", "offset": 5},
            {"label": "file.txt", "filepath": "/file.txt", "offset": 5},
        ], value="open ", placeholder="open /base")
        yield test, "open dir", result([
            {"label": "dir/", "offset": 5},
        ], value="open dir")
        yield test, "open dir/", result([
            {"label": "file.txt", "filepath": "/dir/file.txt", "offset": 9},
        ], value="open dir/")


@yield_test
def test_create_new_file():
    def test(relpath):
        with tempdir() as base:
            filepath = Path(base) / "file.txt"
            filepath.touch()
            assert filepath.exists(), filepath

            path = join(base, relpath)
            mod.create_new_file(path)
            assert exists(path)

    yield test, "file.txt"
    yield test, "dir/file.txt"
    yield test, "new.txt"


@contextmanager
def fake_editor(folders=()):
    with tempdir() as tmp:
        base = Path(tmp) / "base"
        base.mkdir()
        (base / "file.txt").touch()
        (base / "dir").mkdir()
        (base / "dir/file.txt").touch()
        for i, folder in enumerate(folders):
            (base / folder).mkdir()
            (base / folder / f"file{i}.txt").touch()
        yield FakeEditor(str(base / "file.txt"), str(base))


def normalize_paths(items, base):
    for item in items:
        if isinstance(item, dict) and "filepath" in item:
            item["filepath"] = normalize_path(item["filepath"], base)


def normalize_path(path, base):
    assert path.startswith(base)
    return path[len(base):]
