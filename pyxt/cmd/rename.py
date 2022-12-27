from os.path import basename, exists, isdir, join, sep

from ..command import command
from ..parser import Choice, Conditional, File
from ..results import input_required


async def editor_filepath(editor=None):
    if editor is None:
        return None
    return await editor.file_path


def file_exists(arg):
    path = arg.args.name.value
    return path and exists(path)


@command(
    File("name", default=editor_filepath),
    Conditional(
        file_exists,
        Choice(("overwrite", True), (" ", False), default=False),
    ),
    has_history=False,
)
async def rename(editor, args):
    """Rename current editor"""
    if not args.name:
        return input_required("name is required", args)
    if args.name.endswith((sep, "/")) or isdir(args.name):
        name = join(args.name, basename(await editor.file_path))
    else:
        name = args.name
    await editor.rename(name, args.overwrite)
