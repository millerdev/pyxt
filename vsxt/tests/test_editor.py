from contextlib import contextmanager

from testil import eq, replattr

from .. import editor as mod
from ..tests.util import async_test


@async_test
async def test_file_path():
    fsPath = "JSProxy.window.activeTextEditor.document.uri.fsPath"
    with setup_editor() as editor:
        eq(await editor.file_path, fsPath)


def test_project_path():
    @async_test
    async def test(expected_result, calls=None):
        calls = calls or {}
        calls.setdefault(folder_call, None)
        calls.setdefault("JSProxy.workspace.workspaceFolders[0].uri.fsPath", None)
        with setup_editor(calls) as editor:
            eq(await editor.project_path, expected_result)

    active_uri = "JSProxy.window.activeTextEditor.document.uri"
    folder_call = f"JSProxy.workspace.getWorkspaceFolder({active_uri},).uri.fsPath"

    yield test, "/home/user"
    yield test, "/work", {folder_call: "/work"}
    yield test, "/work", {
        "JSProxy.workspace.workspaceFolders[0].uri.fsPath": "/work",
    }


@async_test
async def test_selection():
    sel = "JSProxy.window.activeTextEditor.selection"
    seltext = f"JSProxy.window.activeTextEditor.document.getText({sel},)"
    with setup_editor() as editor:
        eq(await editor.selection, seltext)


@async_test
async def test_selection_with_null_result():
    sel = "JSProxy.window.activeTextEditor.selection"
    seltext = f"JSProxy.window.activeTextEditor.document.getText({sel},)"
    calls = {seltext: None}
    with setup_editor(calls) as editor:
        eq(await editor.selection, "")


@contextmanager
def setup_editor(srv=None):
    with replattr(
        (mod, "expanduser", lambda path: "/home/user"),
        (mod, "get", fake_get),
    ):
        yield mod.Editor(srv or {})


async def fake_get(proxy):
    path = str(proxy)
    calls, params = proxy._resolve()
    return calls.get(path, path)
