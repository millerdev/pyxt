from os.path import dirname, expanduser, isabs

from .jsproxy import EDITOR, JSProxy, VSCODE
from .util import cached_property


class Editor:
    def __init__(self, server):
        self.server = server
        self.vscode = JSProxy(server, root=VSCODE)
        self.editor = JSProxy(server, root=EDITOR)

    @cached_property
    async def file_path(self):
        return await self.vscode.window.activeTextEditor.document.uri.fsPath

    @cached_property
    async def project_path(self):
        file_uri = self.vscode.window.activeTextEditor.document.uri
        if await file_uri.fsPath is not None:
            folder = self.vscode.workspace.getWorkspaceFolder(file_uri)
            path = await folder.uri.fsPath
            if path:
                return path
        path = await self.vscode.workspace.workspaceFolders[0].uri.fsPath
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
        return await path or "ag"

    @cached_property
    async def python_path(self):
        path = self.vscode.workspace.getConfiguration('pyxt').get('pythonPath')
        return await path or "python"

    @cached_property
    async def eol(self):
        eol = await self.vscode.window.activeTextEditor.document.eol
        CRLF = await self.vscode.EndOfLine.CRLF
        return "\r\n" if eol == CRLF else "\n"

    @cached_property
    async def insert_spaces(self):
        return await self.vscode.window.activeTextEditor.options.insertSpaces

    @cached_property
    async def tab_size(self):
        return await self.vscode.window.activeTextEditor.options.tabSize

    def selection(self, range=None):
        return self.editor.selection(range)

    def selections(self, ranges=None):
        return self.editor.selections(ranges)

    def get_text(self, range=None):
        return self.editor.get_text(range)

    def get_texts(self, ranges):
        return self.editor.get_texts(ranges)

    async def set_text(self, text, range=None, select=True):
        await self.editor.set_text(text, range, select)

    async def set_texts(self, texts, ranges):
        await self.editor.set_texts(texts, ranges)

    async def show_message(self, message):
        await self.vscode.window.showInformationMessage(message)

    async def rename(self, path):
        await self.editor.rename(path)
