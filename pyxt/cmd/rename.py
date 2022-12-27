from os.path import basename, isdir, join, sep

from ..command import command
from ..parser import File
from ..results import input_required


async def editor_filepath(editor=None):
    if editor is None:
        return None
    return await editor.file_path


@command(
    File("name", default=editor_filepath),
)
async def rename(editor, args):
    """Rename current editor"""
    if args.name is None:
        return input_required("name is required", args)
    if args.name.endswith((sep, "/")) or isdir(args.name):
        name = join(args.name, basename(await editor.file_path))
    else:
        name = args.name
    await editor.rename(name)
