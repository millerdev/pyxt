from dataclasses import dataclass


@dataclass
class JSProxy:
    _parent: object
    _name: str = None
    _args: tuple = None

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
            return type(self).__name__
        rep = self._name
        if isinstance(rep, int):
            rep = f"[{rep}]"
        else:
            rep = f".{rep}"
        if self._args is not None:
            rep = f"{rep}{self._args}"
        return f"{self._parent}{rep}"

    def __await__(self):
        server, params = self._resolve()
        obj = server.lsp.send_request_async("vsxt.resolve", [params])
        return obj.__await__()

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
        return self._parent, next_value
