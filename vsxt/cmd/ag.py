import asyncio
import logging
import os
import re
import subprocess

from ..command import command, get_context
from ..parser import CommandParser, File, Regex, RegexPattern, String, VarArgs
from ..results import result

log = logging.getLogger(__name__)
AG_LINE = re.compile(r"""
    (?P<num>\d*)                    # line number
    (?P<ranges>;(?:\d+\ \d+,?)*)?   # matched ranges
    (?P<delim>:)                    # delimiter
    (?P<text>.*)                    # line content
""", re.VERBOSE)
DEFAULT_OPTIONS = [
    "--ackmate",
    "--nopager",
    "--nocolor",
]
AG_NOT_INSTALLED = """
{} does not appear to be installed.

See https://github.com/ggreer/the_silver_searcher#the-silver-searcher
"""


async def get_selection_regex(editor=None):
    text = (await editor.selection) if editor else ""
    return RegexPattern(re.escape(text), default_flags=0) if text else None


async def project_dirname(editor=None):
    if editor is None:
        return None
    project_path = await editor.project_path
    return (await editor.dirname) if project_path == "~" else project_path


@command(
    "ag",
    CommandParser(
        Regex("pattern", default=get_selection_regex),
        File("path", default=project_dirname, directory=True),
        VarArgs("options", String("options")),
        # TODO SubParser with dynamic dispatch based on pattern matching
        # (if it starts with a "-" it's an option, otherwise a file path)
    ),
    has_placeholder_item=True,
)
async def ag(editor, args):
    """Search for files matching pattern"""
    if args.pattern is None:
        return input_required("pattern is required", args)
    pattern = args.pattern
    if "-i" in args.options or "--ignore-case" in args.options:
        pattern = RegexPattern(pattern, pattern.flags | re.IGNORECASE)
    elif pattern.flags & re.IGNORECASE:
        args.options.append("--ignore-case")
    ag_path = await editor.ag_path
    options = DEFAULT_OPTIONS
    cwd = args.path or await editor.dirname
    if cwd is None:
        return input_required("path is required", args)
    items = []
    line_processor = make_line_processor(items, ag_path, cwd)
    command = [ag_path, pattern] \
        + [o for o in args.options if o] + options
    try:
        await process_lines(command, cwd=cwd, **line_processor)
    except CommandError as err:
        if not items:
            return input_required(str(err), args)
        items.append({"label": "", "description": str(err)})
    if items:
        drop_redundant_details(items)
    if not args.path:
        args.path = cwd
    placeholder = await get_context(args).command.arg_string(args)
    return result(items, filter_results=True, placeholder=placeholder)


def input_required(message, args):
    cmdstr = get_context(args).input_value
    return result([{"label": "", "description": message}], cmdstr)


def make_line_processor(items, ag_path, cwd):

    async def ag_lines(lines):
        filepath = None
        absfilepath = None
        async for line in lines:
            line = line.rstrip("\n")
            line = line.rstrip("\0")  # bug in ag adds null char to some lines?
            if line.startswith(":"):
                filepath = line[1:]
                absfilepath = os.path.join(cwd, filepath)
            else:
                match = AG_LINE.match(line)
                if match:
                    yield create_item(absfilepath, filepath, **match.groupdict(''))
                elif line:
                    yield {"label": "", "description": line}

    def got_output(item, returncode, error=""):
        if item is not None:
            items.append(item)
        if returncode:
            if is_ag_installed(ag_path):
                if returncode == 1:
                    message = "no match"
                else:
                    message = f"[exit: {returncode}] {error}"
            else:
                message = AG_NOT_INSTALLED.format(ag_path)
            raise CommandError(message)

    return {"iter_output": ag_lines, "got_output": got_output}


def create_item(abspath, relpath, num, ranges, delim, text):
    rng = next(iter(ranges.lstrip(";").split(",")), "")
    if rng:
        start, length = [int(n) for n in rng.split()]
        rng = f":{start}:{length}"
    return {
        "label": f"{num}: {text.strip()}",
        "detail": relpath,
        "filepath": abspath + f":{int(num) - 1}{rng}",
    }


def drop_redundant_details(items):
    detail = None
    for item in reversed(items):
        if "detail" not in item:
            continue
        if item["detail"] == detail:
            item.pop("detail")
        else:
            detail = item["detail"]


async def process_lines(command, *, got_output, kill_on_cancel=True, **kw):
    """Execute shell command, processing output asynchronously

    :param command: The first argument passed to `subprocess.Popen`.
    :param got_output: A two-arg function `got_output(string, returncode)`
    to be called in the main thread. This function may be called
    multiple times with chunks of output received from the process, and
    will be called a final time when the process has terminated. The
    first argument will be `None` on the final call, and the second
    argument will be `None` on all calls except for the final call.
    :param iter_output: An optional generator function taking a single
    argument, the process stdout stream and yielding processed output.
    This generator will be executed in a thread.
    :param kill_on_cancel: When true (the default), kill the subprocess if
    the command is canceled. Otherwise just stop collecting output.
    :param **kw: Keyword arguments accepted by `subprocess.Popen`.
    """
    from asyncio.subprocess import PIPE, STDOUT
    iter_output = kw.pop("iter_output", None)
    env = {k: v for k, v in os.environ.items() if k not in IGNORE_ENV}
    cmd = " ".join(command)
    log.debug("async run: %s", cmd)
    try:
        proc = await asyncio.create_subprocess_exec(
            *command, stdout=PIPE, stderr=STDOUT, env=env, **kw)
    except Exception as err:
        log.warn("cannot open process: %s", cmd, exc_info=True)
        got_output(None, -1, str(err))
        return
    lines = iter_lines(proc.stdout, encoding="utf-8")
    items = lines if iter_output is None else iter_output(lines)
    async for item in items:
        got_output(item, None)
    await proc.wait()
    got_output(None, proc.returncode)


async def iter_lines(stream, encoding):
    while True:
        line = await stream.readline()
        if not line:
            break
        yield line.decode(encoding)


IGNORE_ENV = {}


def is_ag_installed(ag_path="ag", recheck=False, result={}):
    if result.get(ag_path) is not None and not recheck:
        return result.get(ag_path)
    rcode = subprocess.call(
        [ag_path, "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    result[ag_path] = rcode == 0
    return result[ag_path]


class CommandError(Exception):
    pass
