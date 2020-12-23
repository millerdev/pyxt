from os.path import dirname, expanduser, isabs

from .jsproxy import get, JSProxy
from .util import cached_property


class Editor:
    def __init__(self, server):
        self.proxy = JSProxy(server)

    @cached_property
    async def file_path(self):
        return await get(self.proxy.window.activeTextEditor.document.uri.fsPath)

    @cached_property
    async def project_path(self):
        file_uri = self.proxy.window.activeTextEditor.document.uri
        if await get(file_uri.fsPath) is not None:
            folder = self.proxy.workspace.getWorkspaceFolder(file_uri)
            path = await get(folder.uri.fsPath)
            if path:
                return path
        path = await get(self.proxy.workspace.workspaceFolders[0].uri.fsPath)
        return path if path else expanduser("~")

    @cached_property
    async def dirname(self):
        path = await get(self.file_path)
        if path:
            current_dir = dirname(path)
            if current_dir and isabs(current_dir):
                return current_dir
        return await get(self.project_path)

    @cached_property
    async def selection(self):
        sel = self.proxy.window.activeTextEditor.selection
        doc = self.proxy.window.activeTextEditor.document
        return await get(doc.getText(sel)) or ""
