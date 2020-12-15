import os
from os.path import dirname, exists, isabs, isdir
from pathlib import Path

from ..command import command, Incomplete
from ..parser import CommandParser, File
from ..results import result


@command("open", CommandParser(File("path")))
async def open_file(editor, args):
    if not args.path or isdir(args.path):
        raise Incomplete
    prepare_to_open(args.path)
    return result(value=args.path)


def prepare_to_open(path):
    if not exists(path):
        if not isabs(path):
            raise ValueError(f"relative path: {path}")
        if not isdir(dirname(path)):
            os.makedirs(dirname(path))
        Path(path).touch()
