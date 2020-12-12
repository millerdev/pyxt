import os
from os.path import dirname, exists, isabs, isdir
from pathlib import Path

from ..command import command
from ..parser import CommandParser, File, VarArgs
from ..results import result


@command("open", CommandParser(VarArgs("paths", File("path"))))
async def open_file(editor, args):
    paths = args.paths[:1]
    for path in paths:
        prepare_to_open(path)
    return result(value=paths[0] if paths else None)


def prepare_to_open(path):
    if not exists(path):
        if not isabs(path):
            raise ValueError(f"relative path: {path}")
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        Path(path).touch()
