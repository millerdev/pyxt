from inspect import iscoroutine
from os.path import dirname, expanduser, isabs

from .jsproxy import EDITOR, get, JSProxy, VSCODE
from .util import cached_property


class Editor:
    def __init__(self, server):
        self.vscode = JSProxy(server, root=VSCODE)
        self.editor = JSProxy(server, root=EDITOR)

    @cached_property
    async def file_path(self):
        return await get(self.vscode.window.activeTextEditor.document.uri.fsPath)

    @cached_property
    async def project_path(self):
        file_uri = self.vscode.window.activeTextEditor.document.uri
        if await get(file_uri.fsPath) is not None:
            folder = self.vscode.workspace.getWorkspaceFolder(file_uri)
            path = await get(folder.uri.fsPath)
            if path:
                return path
        path = await get(self.vscode.workspace.workspaceFolders[0].uri.fsPath)
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
    async def ag_path(self):
        path = self.vscode.workspace.getConfiguration('pyxt').get('agPath')
        return await get(path) or "ag"

    @cached_property
    async def python_path(self):
        path = self.vscode.workspace.getConfiguration('pyxt').get('pythonPath')
        return await get(path) or "python"

    async def selection(self, range=None):
        sel = await get(self.editor.selection())
        return tuple(sel) if sel else None

    async def get_text(self, range):
        if iscoroutine(range):
            # allows editor.get_text(editor.selection())
            range = await range
        return await get(self.editor.get_text(range))

    async def set_text(self, text, range=None, select=True):
        if iscoroutine(range):
            # allows editor.set_text(value, editor.selection(), ...)
            range = await range
        await get(self.editor.set_text(text, range, select))
