import os
from os.path import expanduser, isdir

from ..results import result


def open_file(server, path, complete=False):
    cmd = f"open {path}"
    if not path:
        path = "." # TODO get current directory from workspace
    elif path.startswith("~"):
        path = expanduser(path)
    if isdir(path):
        if not path.endswith(os.path.sep) and len(cmd) > 5:
            cmd += os.path.sep
        return result(os.listdir(path), cmd, offset=len(cmd))
    if complete:
        return result([], cmd, offset=len(cmd))
    return result(value=path)
