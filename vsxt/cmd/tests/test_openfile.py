from contextlib import contextmanager
from dataclasses import dataclass
from os.path import exists, join
from pathlib import Path

from testil import eq, tempdir

from .. import openfile as mod
from ...tests.util import async_test


def test_open_file():
    with fake_editor() as editor:
        @async_test
        async def test(path, expect):
            result = await mod.open_file(editor, path)
            eq(result["type"], "success", result)
            eq(result["value"], expect.format(base=editor.current_path))

        yield test, "file.txt", "{base}/file.txt"
        yield test, "dir/file.txt", "{base}/dir/file.txt"
        yield test, "../file.txt", "{base}/../file.txt"


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
        yield FakeEditor(str(base))


@dataclass
class FakeEditor:
    current_path: str = None
    work_path: str = None

    @property
    async def current_dir(self):
        return self.current_path

    async def workspace_dir(self):
        return self.work_path
