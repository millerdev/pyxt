import logging
import inspect

from . import command as cmd
from .editor import Editor
from .results import error, result
from .types import XTServer

# register commands by importing them
from .cmd import (  # noqa: F401
    openfile,
)

log = logging.getLogger(__name__)
xt_server = XTServer()


def xt_command(func):
    return xt_server.command(func.__name__)(func)


@xt_command
async def do_command(server: XTServer, params):
    input_value, = params
    if input_value:
        command, input_value = parse_command(input_value)
        if not command:
            return error(f"Unknown command: {input_value!r}")
        editor = Editor(server)
        args = await command.parser.parse(input_value)
        return await command(editor, args)
    return result([])


@xt_command
async def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, input_value = parse_command(input_value)
    else:
        command = None
    if not command:
        return {"items": sorted(cmd.REGISTRY), "offset": 0}
    editor = Editor(server)
    result = command.parser.get_completions(editor, input_value)
    return (await result) if inspect.isawaitable(result) else result


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
    return COMMANDS.get(name), (input_value if name in COMMANDS else name)
