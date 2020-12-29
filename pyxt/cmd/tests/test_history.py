from ...tests.util import async_test, get_completions, FakeEditor


@async_test
async def test_history_completions():
    editor = FakeEditor()
    result = await get_completions("history ", editor)
    items = result["items"]
    assert item("ag") in items, result
    assert item("open") in items, result
    assert item("history") not in items, result


def item(label):
    return {"label": label, "offset": 8}
