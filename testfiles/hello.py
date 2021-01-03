from pyxt.command import command
from pyxt.parser import String
from pyxt.results import result


@command(String("name", default="world"))
async def hello(editor, args):
    return result([f"Hello {args.name}!"])
