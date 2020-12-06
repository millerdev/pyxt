
def result(items=None, value=None, **extra):
    if items is None:
        type = "success"
    else:
        type = "items"
    return {"type": type, **extra, "items": items, "value": value}


def error(message):
    return {"type": "error", "message": message}
