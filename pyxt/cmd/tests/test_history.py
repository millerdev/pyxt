from testil import eq

from ...server import do_command
from ...tests.util import async_test, fake_history, FakeEditor, get_completions


@async_test
async def test_history_clear():
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
async def test_history_command_completions():
    editor = FakeEditor()
    result = await get_completions("history clear ", editor)
    items = result["items"]
    assert item("ag", 14) in items, result
    assert item("open", 14) in items, result
    assert item("history", 14) in items, result


def item(label, offset):
    return {"label": label, "offset": offset}
