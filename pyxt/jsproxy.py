import asyncio
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


VSCODE = "vscode"
EDITOR = "editor"
HISTORY = "history"


@dataclass
class JSProxy:
    _parent: object
    _name: str = None
    _args: tuple = None
    root: str = None

    def __getattr__(self, name):
        return type(self)(self, name)

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise ValueError(f"unsupported key: {key!r}")
        return type(self)(self, key)

    def __call__(self, *args):
        if not self._name:
            raise TypeError(f"{self} is not callable")
        return type(self)(self._parent, self._name, tuple(args))

    def __repr__(self):
        if self._name is None:
            return self.root or type(self).__name__
        rep = self._name
        if isinstance(rep, int):
            rep = f"[{rep}]"
        else:
            rep = f".{rep}"
        if self._args is not None:
            rep = f"{rep}{self._args}"
        return f"{self._parent}{rep}"

    def _resolve(self, next_value=None):
        if self._name is not None:
            value = {"name": self._name}
            if self._args is not None:
                def resolve(arg):
                    if isinstance(arg, JSProxy):
                        server, params = arg._resolve()
                        arg = {**params, "__resolve__": True}
                    return arg
                value["args"] = [resolve(a) for a in self._args]
            if next_value:
                value["next"] = next_value
            return self._parent._resolve(value)
        assert next_value
        assert self.root, self
        return self._parent, {**next_value, "root": self.root}

    def __await__(self):
        return _get(self).__await__()


async def _get(proxy):
    server, params = proxy._resolve()
    value = await server.lsp.send_request_async("pyxt.resolve", [params])
    if isinstance(value, list) and len(value) == 3 and value[0] == "__error__":
        message = value[1] or "unknown error"
        stack = value[2] or message
        log.error("Unhandled client error: %s", stack)
        raise Error(message)
    return value


def async_do(proxy):
    return asyncio.create_task(_get(proxy))


class Error(Exception):
    pass
