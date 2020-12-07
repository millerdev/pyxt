import os
from os.path import dirname, exists, expanduser, isabs, isdir, join
from pathlib import Path

from ..results import result


async def open_file(server, path, complete=False):
    cmd = f"open {path}"
    if not path:
        path = await get_current_dir(server)
    elif path.startswith("~"):
        path = expanduser(path)
    if not isabs(path):
        base = await get_current_dir(server)
        path = join(base, path)
    if isdir(path):
        if not path.endswith(os.path.sep) and len(cmd) > 5:
            cmd += os.path.sep
        return result(os.listdir(path), cmd, offset=len(cmd))
    if complete:
        return result([], cmd, offset=len(cmd))
    prepare_to_open(path)
    return result(value=path)


async def get_current_dir(server):
    prop = "window.activeTextEditor.document.uri.fsPath"
    path = await server.lsp.send_request_async("vsxt.getProp", [prop])
    if path:
        current_dir = dirname(path)
        if current_dir and isabs(current_dir):
            return current_dir
    return "."


def prepare_to_open(path):
    if not exists(path):
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        Path(path).touch()
