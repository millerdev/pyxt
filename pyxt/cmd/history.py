from ..command import command
from ..history import clear, get_history
from ..parser import Choice, DynamicList
from ..results import error, input_required


def get_commands(editor):
    from ..command import REGISTRY
    return [""] + sorted(REGISTRY.keys() - {"history"})


@command(
    Choice("redo", "clear", name="action"),
    DynamicList("command", get_commands, str),
    has_placeholder_item=False,
    has_history=False,
)
async def history(editor, args):
    """Clear command history"""
    if not args.command:
        input_required("choose a command", args)
    if args.action == "clear":
        await clear(editor.server, args.command)
        await editor.show_message(f"{args.command} command history cleared.")
        return
    assert args.action == "redo", args
    items = await get_history(editor.server, args.command)
    if items:
        from ..server import do_command
        return await do_command(editor.server, [items[0]])
    return error(f"{args.command} has no history")
