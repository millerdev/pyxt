import os


def user_path(path, home=os.path.expanduser('~')):
    """Return path with user home prefix replaced with ~ if applicable"""
    if os.path.normpath(path).startswith(home + os.sep):
        path = '~' + os.path.normpath(path)[len(home):]
    return path
