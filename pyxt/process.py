import logging
from asyncio.exceptions import CancelledError
from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT

log = logging.getLogger(__name__)


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
    iter_output = kw.pop("iter_output", None)
    cmd = " ".join(command)
    log.debug("async run: %s", cmd)
    try:
        proc = await create_subprocess_exec(
            *command, stdout=PIPE, stderr=STDOUT, **kw)
    except Exception as err:
        log.warn("cannot open process: %s", cmd, exc_info=True)
        got_output(None, -1, str(err))
        return
    try:
        lines = iter_lines(proc.stdout, encoding="utf-8")
        items = lines if iter_output is None else iter_output(lines)
        async for item in items:
            got_output(item, None)
        await proc.wait()
        got_output(None, proc.returncode)
    except CancelledError:
        log.debug("cancelled: %s", cmd)
        if kill_on_cancel:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass
        # HACK `proc` should have a `close()` method
        # avoid RuntimeError: Event loop is closed
        proc._transport.close()
        raise


async def run_command(command, **kw):
    def got_output(line, returncode, error=""):
        if line is not None:
            lines.append(line)
        if returncode:
            if not error:
                error = "\n".join(lines) or "unknown error"
            raise ProcessError(f"[exit {returncode}] {error}")

    lines = []
    await process_lines(command, got_output=got_output, **kw)
    return "".join(lines)


async def iter_lines(stream, encoding):
    while True:
        line = await stream.readline()
        if not line:
            break
        yield line.decode(encoding)


class ProcessError(Exception):
    pass
