import logging

from . import command as cmd
from .editor import Editor
from .results import error, handle_cancel, result
from .types import XTServer

# register commands by importing them
from .cmd import (  # noqa: F401
    ag,
    history,
    openfile,
)

log = logging.getLogger(__name__)
xt_server = XTServer()


def xt_command(func):
    return xt_server.command(func.__name__)(func)


@xt_command
@handle_cancel
async def do_command(server: XTServer, params):
    input_value, = value, = params
    if not input_value:
        return command_completions()
    command, argstr = parse_command(input_value)
    if not command:
        return error(f"Unknown command: {argstr!r}")
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    args = await parser.parse(argstr)
    cmd.set_context(args, input_value=input_value, command=command)
    try:
        return await command(editor, args)
    except cmd.Incomplete as err:
        value += err.addchars
        argstr += err.addchars
    return await _get_completions(command, parser, value, argstr)


@xt_command
@handle_cancel
async def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, argstr = parse_command(input_value)
    else:
        argstr = ""
        command = None
    if not command:
        return command_completions(argstr)
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    return await _get_completions(command, parser, input_value, argstr)


def parse_command(input_value):
    assert input_value, repr(input_value)
    parts = input_value.split(" ", maxsplit=1)
    name = parts[0]
    if len(parts) > 1:
        assert len(parts) == 2, parts
        argstr = parts[1]
    else:
        argstr = ""
    COMMANDS = cmd.REGISTRY
    if name in COMMANDS:
        return COMMANDS[name], argstr
    return None, name


async def _get_completions(command, parser, input_value, argstr):
    items = await parser.get_completions(argstr)
    if not (argstr or input_value.endswith(" ")):
        input_value += " "
    offset = len(input_value) - len(argstr)
    items = [itemize(x, offset) for x in items]
    if command.has_placeholder_item:
        for item in items:
            item.setdefault("is_completion", True)
        arg_end, hint = await parser.get_placeholder(argstr)
        if arg_end or hint:
            items.insert(0, {
                "label": input_value + arg_end,
                "description": hint,
                "offset": 0,
            })
    return result(items, input_value)


def itemize(item, offset):
    if isinstance(item, str):
        item = {"label": item}
    if "offset" not in item:
        item["offset"] = offset + item["label"].start
    return item


def command_completions(argstr=""):
    items = [{
        "label": name + " ",
        "offset": 0,
        "is_completion": True,
    } for name in cmd.REGISTRY]
    return result(items, argstr)
