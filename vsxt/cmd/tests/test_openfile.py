from os.path import exists, join
from pathlib import Path

from testil import tempdir

from .. import openfile as mod


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
