from contextlib import contextmanager
from os.path import exists, join
from pathlib import Path

from testil import eq, tempdir

from .. import openfile as mod
from ...results import result
from ...tests.util import FakeEditor, async_test, do_command


def test_open_file():
    with fake_editor() as editor:
        @async_test
        async def test(cmdstr, expect):
            result = await do_command(cmdstr, editor)
            if isinstance(expect, str):
                eq(result["type"], "success", result)
                eq(result["value"], expect.format(base=await editor.dirname))
            else:
                eq(result, expect)

        yield test, "open file.txt", "{base}/file.txt"
        yield test, "open dir/file.txt", "{base}/dir/file.txt"
        yield test, "open ../file.txt", "{base}/../file.txt"
        yield test, "open ", result(["dir", "file.txt"], value="open ", offset=5)
        yield test, "open dir", result(["dir/"], value="open dir", offset=5)
        yield test, "open dir/", result(["file.txt"], value="open dir/", offset=9)


def test_parepare_to_open():
    def test(relpath):
        with tempdir() as base:
            filepath = Path(base) / "file.txt"
            filepath.touch()
            assert filepath.exists(), filepath

            path = join(base, relpath)
            mod.prepare_to_open(path)
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
