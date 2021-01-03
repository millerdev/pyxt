from os.path import basename, dirname, exists, join
from pathlib import Path

from ..command import command
from ..parser import Choice, String


async def default_package(editor):
    package = ""
    path = await editor.dirname
    while path and path != dirname(path):
        if exists(join(path, "__init__.py")):
            package = basename(path)
        else:
            break
        path = dirname(path)
    return package


async def default_scope(editor=None):
    start, end = await editor.selection()
    return bool(end - start)


@command(
    String('known_first_party', default=default_package),
    Choice(('selection', True), ('all', False), default=default_scope),
)
async def isort(editor, args):
    from isort.api import sort_code_string
    sel = (await editor.selection()) if args.selection else None
    text = await editor.get_text(sel)
    txt = sort_code_string(
        code=text,
        file_path=Path(await editor.file_path),
        default_section="THIRDPARTY",
        known_first_party=[x for x in args.known_first_party.split(",") if x],
    )
    await editor.set_text(txt, sel, select=args.selection)
