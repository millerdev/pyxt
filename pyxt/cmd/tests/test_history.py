from testil import eq

from ... import command
from ...results import error, result
from ...server import do_command
from ...tests.util import (
    async_test,
    fake_history,
    FakeEditor,
    get_completions,
    test_command,
)


@async_test
async def test_redo():
    registry = command.REGISTRY
    server = {"calls": [], "history.get('cmd',)": ["a", "b"]}
    with fake_history(), test_command(with_history=True):
        command.REGISTRY["history"] = registry["history"]
        actual_result = await do_command(server, ["history redo cmd"])
    eq(actual_result, result(value="a"))


@async_test
async def test_redo_with_no_history():
    registry = command.REGISTRY
    server = {"calls": [], "history.get('cmd',)": []}
    with fake_history(), test_command(with_history=True):
        command.REGISTRY["history"] = registry["history"]
        actual_result = await do_command(server, ["history redo cmd"])
    eq(actual_result, error("cmd has no history"))


@async_test
async def test_clear():
    server = {"calls": []}
    history = {"python": ["~/venv"], "ag": ["x"]}
    with fake_history(history):
        result = await do_command(server, ["history clear python"])
    eq(result, None)
    eq(server["calls"], [
        "history.clear('python',)",
        "vscode.window.showInformationMessage('python command history cleared.',)",
    ])
    eq(history, {"ag": ["x"]})


@async_test
async def test_action_completions():
    editor = FakeEditor()
    result = await get_completions("history ", editor)
    eq([x["label"] for x in result["items"]], ["redo ", "clear "])


@async_test
async def test_command_completions():
    editor = FakeEditor()
    result = await get_completions("history clear ", editor)
    items = [x["label"] for x in result["items"]]
    assert "ag" in items, result
    assert "open" in items, result
    assert "history" not in items, result
