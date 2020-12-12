import os
from os.path import dirname, exists, isabs, isdir
from pathlib import Path

from ..command import command, Incomplete
from ..parser import CommandParser, File, VarArgs
from ..results import result


@command("open", CommandParser(VarArgs("paths", File("path"))))
async def open_file(editor, args):
    paths = [p for p in args.paths[:1] if p]
    if not paths:
        raise Incomplete
    for path in paths:
        prepare_to_open(path)
    return result(value=paths[0])


def prepare_to_open(path):
    if not exists(path):
        if not isabs(path):
            raise ValueError(f"relative path: {path}")
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        Path(path).touch()
