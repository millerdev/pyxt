import os
import re
import subprocess

from ..command import command, get_context
from ..parser import File, Regex, RegexPattern, String, VarArgs
from ..process import process_lines
from ..results import input_required, error, result

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
{} not found. It may be necessary to set the ag executable path in the
extension settings.

For installation instructions, see
https://github.com/ggreer/the_silver_searcher#the-silver-searcher
"""


async def get_selection_regex(editor=None):
    text = (await editor.get_text(editor.selection())) if editor else ""
    return RegexPattern(escape(text), default_flags=0) if text else None


async def project_dirname(editor=None):
    if editor is None:
        return None
    project_path = await editor.project_path
    return (await editor.dirname) if project_path == "~" else project_path


@command(
    Regex("pattern", default=get_selection_regex, delimiters="'\""),
    File("path", default=project_dirname, directory=True),
    VarArgs("options", String("options")),
    # TODO SubParser with dynamic dispatch based on pattern matching
    # (if it starts with a "-" it's an option, otherwise a file path)
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
    command = [ag_path, pattern] + [o for o in args.options if o] + options
    try:
        await process_lines(command, cwd=cwd, **line_processor)
    except AgNotFound:
        return error(AG_NOT_INSTALLED.format(ag_path))
    except CommandError as err:
        if not items:
            return input_required(str(err), args)
        items.append({"label": "", "description": str(err)})
    if items:
        drop_redundant_details(items)
    if not args.path:
        args.path = cwd
    placeholder = await get_context(args).parser.arg_string(args)
    return result(items, filter_results=True, placeholder=placeholder)


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
            if not is_ag_installed(ag_path):
                raise AgNotFound
            if returncode == 1:
                message = "no match"
            else:
                message = f"[exit: {returncode}] {error}"
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


def escape(text):
    """Like re.escape(), but does not escape spaces"""
    return re.escape(text).replace("\\ ", " ")


def is_ag_installed(ag_path="ag", recheck=False, result={}):
    if result.get(ag_path) is not None and not recheck:
        return result.get(ag_path)
    try:
        rcode = subprocess.call(
            [ag_path, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        rcode = -1
    result[ag_path] = rcode == 0
    return result[ag_path]


class CommandError(Exception):
    pass


class AgNotFound(CommandError):
    pass
