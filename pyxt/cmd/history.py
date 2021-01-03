from ..command import command
from ..parser import DynamicList
from ..results import input_required, result


def get_commands(editor):
    from ..command import REGISTRY
    return sorted(REGISTRY.keys() - {"history"})


@command(DynamicList("command", get_commands, str), has_placeholder_item=False)
async def history(editor, args):
    """Clear command history"""
    if not args.command:
        input_required("enter a command", args)
    return result([], clear_history=True, command=args.command)
