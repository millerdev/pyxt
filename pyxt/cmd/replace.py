import re

from ..command import command
from ..parser import Choice, Regex
from ..results import input_required


@command(
    Regex("pattern", replace=True),
    Choice("selection all", name="action"),
    Choice("regex literal word", name="search_type"),
)
async def replace(editor, args):
    """Find and replace text"""
    if args.pattern is None:
        return input_required("pattern is required", args)
    find, replace = args.pattern
    flags = find.flags
    if args.search_type == "literal":
        find = re.escape(find)
    elif args.search_type == "word":
        find = f"\\b{find}\\b"
    regex = re.compile(find, flags)
    if args.action == "all":
        texts = [await editor.get_text()]
        ranges = [(0, len(texts[0]))]
    else:
        ranges = await editor.selections()
        texts = await editor.get_texts(ranges)
    texts = [regex.sub(replace, t) for t in texts]
    await editor.set_texts(texts, ranges)
