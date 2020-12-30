from pyxt.command import command
from pyxt.parser import CommandParser, String
from pyxt.results import result


@command(parser=CommandParser(String("name", default="world")))
async def hello(editor, args):
    return result([f"Hello {args.name}!"])
