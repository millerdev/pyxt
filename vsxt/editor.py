from os.path import dirname, expanduser, isabs

from .jsproxy import JSProxy
from .util import cached_property


class Editor:
    def __init__(self, server):
        self.proxy = JSProxy(server)

    @cached_property
    async def file_path(self):
        return await self.proxy.window.activeTextEditor.document.uri.fsPath

    @cached_property
    async def project_path(self):
        file_uri = self.proxy.window.activeTextEditor.document.uri
        folder = self.proxy.workspace.getWorkspaceFolder(file_uri)
        path = await folder.uri.fsPath
        if path:
            return path
        path = await self.proxy.workspace.workspaceFolders[0].uri.fsPath
        return path if path else expanduser("~")

    @cached_property
    async def dirname(self):
        path = await self.file_path
        if path:
            current_dir = dirname(path)
            if current_dir and isabs(current_dir):
                return current_dir
        return await self.project_path

    @cached_property
    async def selection(self):
        sel = self.proxy.window.activeTextEditor.selection
        doc = self.proxy.window.activeTextEditor.document
        return await doc.getText(sel) or ""
