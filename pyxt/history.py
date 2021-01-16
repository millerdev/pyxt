from .jsproxy import async_do, HISTORY, JSProxy

LIMIT = 10
cache = {}


def update_history(server, input_value, command):
    assert input_value.startswith(command.name + " "), (command.name, input_value)
    value = input_value[len(command.name) + 1:]
    if value:
        history = JSProxy(server, root=HISTORY)
        async_do(history.update(command.name, value))
        update_local_cache(command.name, value)


def update_local_cache(cmd, value):
    items = cache.setdefault(cmd, [])
    if not (items and value == items[-1]):
        if value in items:
            items = cache[cmd] = [x for x in items if x != value]
        items.append(value)
        if len(items) > LIMIT:
            del items[:-LIMIT]


def should_update_history(input_value, command, result):
    return (
        command.has_history and
        len(input_value) > len(command.name) and
        (result or {}).get("type") != "error"
    )
