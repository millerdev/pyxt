import logging

from pygls.server import LanguageServer

from .cmd.openfile import open_file
from .results import error, result

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


COMMANDS = {
    "open": open_file,
}
