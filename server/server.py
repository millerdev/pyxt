import logging
import os
from os.path import expanduser, isdir

from pygls.server import LanguageServer

log = logging.getLogger(__name__)
XTServer = LanguageServer
xt_server = XTServer()


def xt_command(func):
    return xt_server.command(func.__name__)(func)


@xt_command
def do_command(server: XTServer, params):
    input_value, = params
    if input_value:
        command, input_value = parse_command(input_value)
        if not command:
            return error(f"Unknown command: {input_value!r}")
        return command(server, input_value)
    return result([])


@xt_command
def get_completions(server: XTServer, params):
    input_value, = params
    if input_value:
        command, input_value = parse_command(input_value)
    else:
        command = None
    if not command:
        return {"items": list(COMMANDS), "offset": 0}
    return command(server, input_value, complete=True)


def parse_command(input_value):
    assert input_value, repr(input_value)
    parts = input_value.split(maxsplit=1)
    cmd = parts[0]
    if len(parts) > 1:
        assert len(parts) == 2, parts
        input_value = parts[1]
    else:
        input_value = ""
    return COMMANDS.get(cmd), (input_value if cmd in COMMANDS else cmd)


def open_file(server, path, complete=False):
    cmd = f"open {path}"
    if not path:
        path = "." # TODO get current directory from workspace
    elif path.startswith("~"):
        path = expanduser(path)
    if isdir(path):
        if not path.endswith(os.path.sep) and len(cmd) > 5:
            cmd += os.path.sep
        return result(os.listdir(path), cmd, offset=len(cmd))
    if complete:
        return result([], cmd, offset=len(cmd))
    return result(value=path)


COMMANDS = {
    "open": open_file,
}


def result(items=None, value=None, **extra):
    if items is None:
        type = "success"
    else:
        type = "items"
    return {"type": type, **extra, "items": items, "value": value}


def error(message):
    return {"type": "error", "message": message}
