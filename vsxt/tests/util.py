import asyncio
from dataclasses import dataclass
from functools import wraps
from os.path import dirname

from nose.tools import nottest
from testil import replattr

from .. import server


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


async def do_command(input_value, editor=None):
    if editor is None:
        editor = FakeEditor()
    srv = object()
    with replattr(server, "Editor", lambda srv: editor):
        return await server.do_command(srv, [input_value])


@dataclass
class FakeEditor:
    _file_path: str = None
    _project_path: str = None

    @property
    async def file_path(self):
        return self._file_path

    @property
    async def project_path(self):
        return self._project_path

    @property
    async def dirname(self):
        filepath = await self.file_path
        return dirname(filepath) if filepath else None
