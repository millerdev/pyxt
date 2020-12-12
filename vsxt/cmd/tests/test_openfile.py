from contextlib import contextmanager
from dataclasses import dataclass
from os.path import dirname, exists, join
from pathlib import Path

from testil import eq, tempdir

from .. import openfile as mod
from ...server import parse_command
from ...tests.util import async_test


def test_parse_command():
    def test(input_value, expected_args="", found=True):
        command, args = parse_command(input_value)
        if found:
            assert command is not None, f"command not found: {input_value}"
        else:
            assert command is None, f"unexpected command: {command}"
        eq(args, expected_args)

    yield test, "op", "op", False
    yield test, "ope n", "ope", False
    yield test, "open"
    yield test, "open file", "file"
    yield test, "open a b", "a b"


def test_open_file():
    with fake_editor() as editor:
        @async_test
        async def test(path, expect):
            parser = mod.open_file.parser.with_context(editor)
            args = parser.parse(path)
            result = await mod.open_file(editor, args)
            eq(result["type"], "success", result)
            eq(result["value"], expect.format(base=editor.dirname()))

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
        yield FakeEditor(str(base / "file.txt"), str(base))


@dataclass
class FakeEditor:
    filepath: str = None
    project_path: str = None

    def dirname(self):
        return dirname(self.filepath) if self.filepath else None
