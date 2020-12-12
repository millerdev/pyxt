from dataclasses import dataclass


@dataclass
class JSProxy:
    _parent: object
    _name: str = None

    def __getattr__(self, name):
        return type(self)(self, name)

    def __str__(self):
        if not self._name:
            return type(self).__name__
        rep = self._name
        return f"{self._parent}.{rep}"

    def __await__(self):
        server, params = self._resolve()
        obj = server.lsp.send_request_async("vsxt.resolve", [params])
        return obj.__await__()

    def _resolve(self, next_value=None):
        if self._name:
            value = {"name": self._name}
            if next_value:
                value["next"] = next_value
            return self._parent._resolve(value)
        assert next_value
        return self._parent, next_value
