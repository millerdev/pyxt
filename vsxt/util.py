import os
from asyncio import ensure_future, iscoroutinefunction


def user_path(path, home=os.path.expanduser('~')):
    """Return path with user home prefix replaced with ~ if applicable"""
    if os.path.normpath(path).startswith(home + os.sep):
        path = '~' + os.path.normpath(path)[len(home):]
    return path


class cached_property:

    def __init__(self, func):
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = self.func(obj)
        if iscoroutinefunction(self.func):
            value = ensure_future(value)
        obj.__dict__[self.func.__name__] = value
        return value
