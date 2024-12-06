import ast
import logging
import os
from shutil import which
from textwrap import dedent

from ..command import command, Incomplete
from ..parser import Choice, File, String, VarArgs
from ..process import run_command
from ..results import error, result

log = logging.getLogger(__name__)


async def get_python_executable(editor=None):
    path = await editor.python_path
    return path if os.path.sep in path else which(path)


async def default_scope(editor):
    a, b = await editor.selection() or (0, 0)
    return "all" if a == b else "selection"


@command(
    File("executable", default=get_python_executable),
    Choice("all", "selection", name="scope", default=default_scope),
    VarArgs("options", String("options")),
)
async def python(editor, args):
    """Run the contents of the editor or selection in Python

    executable may be a python interpreter executable or a directory
    such as a virtualenv containing `bin/python`.
    """
    python = args.executable
    if not python:
        raise Incomplete("please specify python executable")
    if os.path.isdir(python):
        bin = os.path.join(python, "bin", "python")
        if os.path.exists(bin):
            python = bin
        else:
            return error("not found: %s" % bin)
    cwd = await editor.dirname
    command = [python] + [o for o in args.options if o]
    if "-c" not in args.options:
        command.extend(["-c", await get_code(editor, args.scope)])
    output = await run_command(command, cwd=cwd)
    message = str(output)
    if message.endswith("\n"):
        message = message[:-1]
    if not message:
        message = "no output"
    return result([
        {"label": message, "copy": True},
    ], filter_results=True)


async def get_code(editor, scope):
    if scope == "selection":
        code = "\n".join(await editor.get_texts(editor.selections()))
    else:
        code = await editor.get_text()
    return print_last_line(dedent(code))


def print_last_line(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        offset = get_node_offset(tree.body[-1], code)
        code = "".join([
            code[:offset],
            "__result__ = ",
            code[offset:],
            "\nif __result__ is not None: print(__result__)",
        ])
    return code


def get_node_offset(node, code):
    if node.lineno == 1:
        return node.col_offset
    total = 0
    for num, line in enumerate(code.splitlines(True), start=1):
        if num == node.lineno:
            return total + node.col_offset
        total += len(line)
    raise ValueError("line out of bounds: {}".format(node.lineno))
