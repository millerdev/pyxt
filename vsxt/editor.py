from os.path import dirname, expanduser, isabs

from .jsproxy import JSProxy


class Editor:
    def __init__(self, server):
        self.proxy = JSProxy(server)

    @property
    async def file_path(self):
        return await self.proxy.window.activeTextEditor.document.uri.fsPath

    @property
    async def project_path(self):
        raise NotImplementedError

    @property
    async def dirname(self):
        path = await self.file_path
        if path:
            current_dir = dirname(path)
            if current_dir and isabs(current_dir):
                return current_dir
        folders = await self.proxy.workspace.workspaceFolders
        if folders:
            return folders[0]
        return expanduser("~")
