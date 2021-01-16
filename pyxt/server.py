import logging

from . import command as cmd
from .editor import Editor
from .results import error, handle_cancel, result
from .types import PyXTServer

# register commands by importing them
from .cmd import (  # noqa: F401
    ag,
    history,
    isort,
    openfile,
    python,
)
from . import custom

log = logging.getLogger(__name__)
pyxt_server = PyXTServer()


def pyxt_command(func):
    return pyxt_server.command(func.__name__)(func)


load_user_script = pyxt_command(custom.load_user_script)


@pyxt_command
@handle_cancel
async def do_command(server: PyXTServer, params):
    input_value, = value, = params
    if not input_value:
        return command_completions()
    command, argstr = parse_command(input_value)
    if not command:
        return error(f"Unknown command: {argstr!r}")
    editor = Editor(server)
    parser = await command.create_parser(editor)
    try:
        args = await parser.parse(argstr)
        cmd.set_context(args, input_value=input_value, parser=parser)
        return await command(editor, args)
    except cmd.Incomplete as err:
        value += err.addchars
        argstr += err.addchars
    except Exception as err:
        log.exception("command error")
        return error(str(err))
    return await _get_completions(command, parser, value, argstr)


@pyxt_command
@handle_cancel
async def get_completions(server: PyXTServer, params):
    input_value, = params
    if input_value:
        command, argstr = parse_command(input_value)
    else:
        argstr = ""
        command = None
    if not command:
        return command_completions(argstr)
    editor = Editor(server)
    parser = await command.create_parser(editor)
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
    has_space_after_command = argstr or input_value.endswith(" ")
    if not has_space_after_command:
        input_value += " "
    offset = len(input_value) - len(argstr)
    items = [itemize(x, offset) for x in items]
    options = {}
    if command.has_placeholder_item:
        for item in items:
            item.setdefault("is_completion", True)
        args, hint = await parser.get_placeholder(argstr)
        if hint:
            options["placeholder"] = hint
        if args or hint:
            items.insert(0, {
                "label": f"{command.name} {args}" if args else command.name,
                "description": hint,
                "offset": 0,
            })
    elif not argstr:
        args, hint = await parser.get_placeholder(argstr)
        if hint:
            options["placeholder"] = input_value + hint
    return result(items, input_value, **options)


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
    } for name in sorted(cmd.REGISTRY)]
    return result(items, argstr)
