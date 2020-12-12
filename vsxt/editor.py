from os.path import dirname, expanduser, isabs

from .jsproxy import JSProxy


class Editor:
    def __init__(self, server):
        self.proxy = JSProxy(server)

    @property
    async def current_dir(self):
        proxy = self.proxy
        path = await proxy.window.activeTextEditor.document.uri.fsPath
        if path:
            current_dir = dirname(path)
            if current_dir and isabs(current_dir):
                return current_dir
        folders = await proxy.workspace.workspaceFolders
        if folders:
            return folders[0]
        return expanduser("~")
