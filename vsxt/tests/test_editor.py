from contextlib import contextmanager

from testil import eq, replattr

from .. import editor as mod
from ..jsproxy import Error
from ..tests.util import async_test, gentest


@async_test
async def test_file_path():
    fsPath = "JSProxy.window.activeTextEditor.document.uri.fsPath"
    with setup_editor() as editor:
        eq(await editor.file_path, fsPath)


def test_project_path():
    @async_test
    async def test(expected_result, calls=None):
        calls = calls or {}
        calls.setdefault(ACTIVE_PATH, object)
        calls.setdefault(FOLDER_CALL, None)
        calls.setdefault(FIRST_WORKSPACE, None)
        with setup_editor(calls) as editor:
            eq(await editor.project_path, expected_result)

    yield test, "/home/user"
    yield test, "/work", {FOLDER_CALL: "/work"}
    yield test, "/space", {FIRST_WORKSPACE: "/space"}
    yield test, "/project", {
        ACTIVE_PATH: None,
        FOLDER_CALL: Error,
        FIRST_WORKSPACE: "/project",
    }


def test_dirname():
    @gentest
    @async_test
    async def test(expected_path, file_path=None, project_path=None):
        calls = {
            ACTIVE_PATH: file_path,
            FIRST_WORKSPACE: project_path,
        }
        with setup_editor(calls) as editor:
            eq(await editor.dirname, expected_path)

    yield test("/home/user")
    yield test("/path/to", file_path="/path/to/file")
    yield test("/project/path", file_path=None, project_path="/project/path")


@async_test
async def test_ag_path():
    with setup_editor() as editor:
        eq(
            await editor.ag_path,
            "JSProxy.workspace.getConfiguration('vsxt',).get('agPath',)",
        )


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


ACTIVE_URI = "JSProxy.window.activeTextEditor.document.uri"
ACTIVE_PATH = f"{ACTIVE_URI}.fsPath"
FOLDER_CALL = f"JSProxy.workspace.getWorkspaceFolder({ACTIVE_URI},).uri.fsPath"
FIRST_WORKSPACE = "JSProxy.workspace.workspaceFolders[0].uri.fsPath"


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
    value = calls.get(path, path)
    if value is Error:
        raise value
    return value
