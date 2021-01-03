import os
from os.path import dirname, exists, expanduser, isabs, isdir, join, sep
from pathlib import Path

from ..command import command, Incomplete
from ..parser import CompletionsList, File
from ..results import result


class FilePath(File):

    async def get_completions(self, arg):
        items = await super().get_completions(arg)
        if isinstance(items, CompletionsList):
            root = expanduser(items.title)
            for i, item in enumerate(list(items)):
                if not item.endswith(sep):
                    filepath = join(root, item)
                    items[i] = {"label": item, "filepath": filepath}
        return items


@command(
    FilePath("path"),
    name="open",
    has_placeholder_item=False,
    has_history=False,
)
async def open_file(editor, args):
    if not args.path or isdir(args.path):
        raise Incomplete
    if not exists(args.path):
        create_new_file(args.path)
    return result(value=args.path)


def create_new_file(path):
    if not isabs(path):
        raise ValueError(f"relative path: {path}")
    if not isdir(dirname(path)):
        os.makedirs(dirname(path))
    Path(path).touch()
