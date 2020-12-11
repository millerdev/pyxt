from os.path import dirname, expanduser, isabs
from dataclasses import dataclass


class Editor:
    def __init__(self, server):
        self.code = VSProxy(server)

    @property
    async def current_dir(self):
        code = self.code
        path = await code.window.activeTextEditor.document.uri.fsPath
        if path:
            current_dir = dirname(path)
            if current_dir and isabs(current_dir):
                return current_dir
        folders = await code.workspace.workspaceFolders
        if folders:
            return folders[0]
        return expanduser("~")


@dataclass
class VSProxy:
    _parent: object
    _name: str = None

    def __getattr__(self, name):
        return type(self)(self, name)

    def __str__(self):
        if not self._name:
            return "vscode"
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
