import importlib.util as util
import sys
from os.path import isabs, expanduser

from .results import error


def load_user_script(params):
    try:
        path, = params
        if isabs(expanduser(path)):
            spec = util.spec_from_file_location("pyxt.userscript", expanduser(path))
        else:
            spec = util.find_spec(path)
        if not spec:
            return error(f"Cannot import user script: {path}")
        add_pyxt_to_sys_modules()
        userscript = util.module_from_spec(spec)
        spec.loader.exec_module(userscript)
    except Exception as err:
        return error(f"Cannot load user script: {err}")


def add_pyxt_to_sys_modules():
    if "pyxt" not in sys.modules:
        import pyxt  # noqa: F401
        assert "pyxt" in sys.modules, sys.path
