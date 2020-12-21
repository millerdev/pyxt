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
    command, input_value, offset = parse_command(input_value)
    if not command:
        return error(f"Unknown command: {input_value!r}")
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    args = await parser.parse(input_value)
    try:
        return await command(editor, args)
    except cmd.Incomplete as err:
        value += err.addchars
        input_value += err.addchars
    return await _get_completions(value, parser, input_value, offset)


@xt_command
async def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, input_value, offset = parse_command(input_value)
    else:
        offset = None
        command = None
    if not command:
        return result(sorted(cmd.REGISTRY), input_value, offset=0)
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    return await _get_completions(params[0], parser, input_value, offset)


def parse_command(input_value):
    assert input_value, repr(input_value)
    parts = input_value.split(" ", maxsplit=1)
    name = parts[0]
    if len(parts) > 1:
        assert len(parts) == 2, parts
        input_value = parts[1]
    else:
        input_value = ""
    COMMANDS = cmd.REGISTRY
    if name in COMMANDS:
        return COMMANDS[name], input_value, len(name) + 1
    return None, name, 0


async def _get_completions(value, parser, input_value, offset):
    items = await parser.get_completions(input_value)
    if not items:
        placeholder = await parser.get_placeholder(input_value)
        if placeholder:
            command = value.ljust(offset) + placeholder
            items.append({"label": "", "description": command})
            items.offset = len(input_value)
    return result(items, value.ljust(offset), offset=offset + items.offset)
