from contextlib import contextmanager

from testil import eq, replattr

from .. import editor as mod
from .. import jsproxy
from ..tests.util import async_test, gentest


@async_test
async def test_file_path():
    fsPath = "vscode.window.activeTextEditor.document.uri.fsPath"
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
        FOLDER_CALL: jsproxy.Error,
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
            "vscode.workspace.getConfiguration('pyxt',).get('agPath',)",
        )


@async_test
async def test_python_path():
    with setup_editor() as editor:
        eq(
            await editor.python_path,
            "vscode.workspace.getConfiguration('pyxt',).get('pythonPath',)",
        )


@async_test
async def test_selection():
    with setup_editor({"editor.selection(None,)": [1, 2]}) as editor:
        eq(await editor.selection(), [1, 2])


@async_test
async def test_selections():
    with setup_editor({"editor.selections(None,)": [[1, 2], [5, 7]]}) as editor:
        eq(await editor.selections(), [[1, 2], [5, 7]])


@async_test
async def test_selection_with_null_result():
    calls = {"editor.selection(None,)": None}
    with setup_editor(calls) as editor:
        eq(await editor.selection(), None)


@async_test
async def test_get_text():
    selection = "editor.selection(None,)"
    get_text = f"editor.get_text({selection},)"
    with setup_editor({get_text: "text"}) as editor:
        eq(await editor.get_text(editor.selection()), "text")


ACTIVE_URI = "vscode.window.activeTextEditor.document.uri"
ACTIVE_PATH = f"{ACTIVE_URI}.fsPath"
FOLDER_CALL = f"vscode.workspace.getWorkspaceFolder({ACTIVE_URI},).uri.fsPath"
FIRST_WORKSPACE = "vscode.workspace.workspaceFolders[0].uri.fsPath"


@contextmanager
def setup_editor(srv=None):
    with replattr(
        (mod, "expanduser", lambda path: "/home/user"),
        (jsproxy, "_get", fake_get),
    ):
        yield mod.Editor(srv or {})


async def fake_get(proxy):
    path = str(proxy)
    calls, params = proxy._resolve()
    value = calls.get(path, path)
    if value is jsproxy.Error:
        raise value
    return value
