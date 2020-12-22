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
    command, argstr = parse_command(input_value)
    if not command:
        return error(f"Unknown command: {argstr!r}")
    editor = Editor(server)
    parser = await command.parser.with_context(editor)
    args = await parser.parse(argstr)
    cmd.set_context(args, input_value=input_value)
    try:
        return await command(editor, args)
    except cmd.Incomplete as err:
        value += err.addchars
        argstr += err.addchars
    return await _get_completions(command, parser, value, argstr)


@xt_command
async def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, argstr = parse_command(input_value)
    else:
        argstr = ""
        command = None
    if not command:
        return result(sorted(cmd.REGISTRY), argstr, offset=0)
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
    offset = get_offset(input_value, argstr, items)
    if command.has_placeholder_item:
        items = [itemize(x, is_completion=True) for x in items]
        placeholder = await parser.get_placeholder(argstr)
        if placeholder:
            cmdstr = input_value + placeholder
            items.insert(0, {"label": "", "description": cmdstr})
    return result(items, input_value, offset=offset)


def get_offset(input_value, argstr, items):
    if items:
        item = items[0]
        start = item["label"].start if isinstance(item, dict) else item.start
        return len(input_value) - len(argstr) + start
    return len(input_value)


def itemize(item, **extra):
    item = {"label": item} if isinstance(item, str) else item
    item.update(extra)
    return item
