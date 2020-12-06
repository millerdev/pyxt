import os
from os.path import abspath, dirname, exists, expanduser, isabs, isdir
from pathlib import Path

from ..results import result
from ..types import XTServer


async def open_file(server, path, complete=False):
    cmd = f"open {path}"
    if not path:
        path = await get_current_dir(server)
    elif path.startswith("~"):
        path = expanduser(path)
    if not isabs(path):
        path = abspath(path)
    if isdir(path):
        if not path.endswith(os.path.sep) and len(cmd) > 5:
            cmd += os.path.sep
        return result(os.listdir(path), cmd, offset=len(cmd))
    if complete:
        return result([], cmd, offset=len(cmd))
    prepare_to_open(path)
    return result(value=path)


async def get_current_dir(server: XTServer):
    if server.workspace.root_uri:
        return server.workspace.root_uri
    return "."


def prepare_to_open(path):
    if not exists(path):
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        Path(path).touch()
