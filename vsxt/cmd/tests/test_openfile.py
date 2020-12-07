import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from os.path import dirname, exists, join
from pathlib import Path

from nose.tools import nottest
from testil import eq, tempdir

from .. import openfile as mod


def test_open_file():
    @async_test
    async def test(path, expect):
        with fake_server() as server:
            result = await mod.open_file(server, path)
            base = dirname(server.active_path)
            eq(result["type"], "success", result)
            eq(result["value"], expect.format(base=base))

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
def fake_server():
    with tempdir() as tmp:
        base = Path(tmp) / "base"
        base.mkdir()
        yield FakeServer(str(base / "current.txt"))


@dataclass
class FakeServer:
    active_path: str = None
    work_path: str = None

    @property
    def lsp(self):
        return self

    @property
    def _props(self):
        return {
            "window.activeTextEditor.document.uri.fsPath": self.active_path,
        }

    async def send_request_async(self, command, params):
        if command == "vsxt.getProp":
            prop, = params
            return self._props[prop]
        raise RuntimeError(f"unknown command: {command}")


@nottest
def async_test(func):
    @wraps(func)
    def test(*args, **kw):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(func(*args, **kw))
        finally:
            loop.close()
    return test
