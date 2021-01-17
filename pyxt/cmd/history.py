from ..command import command
from ..history import clear
from ..parser import Choice, DynamicList
from ..results import input_required


def get_commands(editor):
    from ..command import REGISTRY
    return [""] + sorted(REGISTRY.keys())


@command(
    Choice("", "clear", name="action"),
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
    else:
        input_required("choose an action", args)
