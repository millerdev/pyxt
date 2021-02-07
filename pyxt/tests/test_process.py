from testil import eq

from .util import async_test
from ..process import process_lines


@async_test
async def test_process_lines_length_limit():
    def got_output(line, code):
        if line is not None:
            lines.append(line)
    lines = []
    cmd = ["echo", "line 1\nline 1 000 000 000\nline 20\nline 30"]
    await process_lines(cmd, got_output=got_output, limit=6)
    eq(lines, ["line 1\n", "line 1", "line 2", "line 3"])
