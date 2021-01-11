import logging
from asyncio.exceptions import CancelledError
from functools import wraps

from .command import get_context

log = logging.getLogger(__name__)


def result(items=None, value=None, **extra):
    if items is None:
        type = "success"
    else:
        type = "items"
    return {"type": type, **extra, "items": items, "value": value}


def input_required(message, args):
    cmdstr = get_context(args).input_value
    return result([{"label": "", "description": message}], cmdstr)


def error(message):
    return {"type": "error", "message": message}


def handle_cancel(func):
    @wraps(func)
    async def decorator(*args, **kw):
        try:
            return await func(*args, **kw)
        except CancelledError:
            return
        except Exception:
            log.exception("unhandled error")
            raise
    return decorator
