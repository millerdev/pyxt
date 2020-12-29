from .util import input_required
from ..command import command
from ..parser import CommandParser, DynamicList
from ..results import result


def get_commands(editor):
    from ..command import REGISTRY
    return sorted(REGISTRY.keys() - {"history"})


@command("history", CommandParser(DynamicList("command", get_commands, str)))
async def history(editor, args):
    """Clear command history"""
    if not args.command:
        input_required("enter a command", args)
    return result([], clear_history=True, command=args.command)
