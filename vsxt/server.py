import logging

from . import command as cmd
from .editor import Editor
from .results import error, result
from .types import XTServer

# register commands by importing them
from .cmd import (  # noqa: F401
    ag,
    openfile,
)

log = logging.getLogger(__name__)
xt_server = XTServer()


def xt_command(func):
    return xt_server.command(func.__name__)(func)


@xt_command
async def do_command(server: XTServer, params):
    input_value, = value, = params
    if not input_value:
        return result(sorted(cmd.REGISTRY), "", offset=0)
    command, argstr, offset = parse_command(input_value)
    if not command:
        return error(f"Unknown command: {argstr!r}")
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    args = await parser.parse(argstr)
    try:
        return await command(editor, args)
    except cmd.Incomplete as err:
        value += err.addchars
        argstr += err.addchars
    return await _get_completions(value, parser, argstr, offset)


@xt_command
async def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, argstr, offset = parse_command(input_value)
    else:
        argstr = ""
        offset = None
        command = None
    if not command:
        return result(sorted(cmd.REGISTRY), argstr, offset=0)
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    return await _get_completions(input_value, parser, argstr, offset)


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
        return COMMANDS[name], argstr, len(name) + 1
    return None, name, 0


async def _get_completions(input_value, parser, argstr, offset):
    input_value = input_value.ljust(offset)
    items = await parser.get_completions(argstr)
    if not items:
        placeholder = await parser.get_placeholder(argstr)
        if placeholder:
            command = input_value + placeholder
            items.append({"label": "", "description": command})
            items.offset = len(argstr)
    return result(items, input_value, offset=offset + items.offset)
