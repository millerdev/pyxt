
from asyncio.exceptions import CancelledError
from functools import wraps


def result(items=None, value=None, **extra):
    if items is None:
        type = "success"
    else:
        type = "items"
    return {"type": type, **extra, "items": items, "value": value}


def error(message):
    return {"type": "error", "message": message}


def handle_cancel(func):
    @wraps(func)
    async def decorator(*args, **kw):
        try:
            return await func(*args, **kw)
        except CancelledError:
            return
    return decorator
