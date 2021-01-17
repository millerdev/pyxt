from .jsproxy import async_do, get, HISTORY, JSProxy

LIMIT = 10
cache = {}


async def get_history(server, command_name, argstr=""):
    if command_name not in cache:
        history = JSProxy(server, root=HISTORY)
        cache[command_name] = await get(history.get(command_name))
    items = cache[command_name]
    cmd = command_name + " "
    return [cmd + x for x in items if x.startswith(argstr)]


def update_history(server, input_value, command):
    assert input_value.startswith(command.name + " "), (command.name, input_value)
    value = input_value[len(command.name) + 1:]
    if value:
        history = JSProxy(server, root=HISTORY)
        async_do(history.update(command.name, value))
        update_local_cache(command.name, value)


async def clear(server, command_name):
    history = JSProxy(server, root=HISTORY)
    await get(history.clear(command_name))
    cache.pop(command_name, None)


def update_local_cache(cmd, value):
    items = cache.setdefault(cmd, [])
    if not (items and value == items[0]):
        if value in items:
            items = cache[cmd] = [x for x in items if x != value]
        if len(items) >= LIMIT:
            del items[LIMIT - 1:]
        items.insert(0, value)


def should_update_history(input_value, command, result):
    return (
        command.has_history and
        len(input_value) > len(command.name) and
        (result or {}).get("type") != "error"
    )
