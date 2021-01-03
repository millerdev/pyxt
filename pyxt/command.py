from .parser import CommandParser, Options

REGISTRY = {}


def command(
    *fields,
    name=None,
    is_enabled=None,
    lookup_with_parser=False,
    has_placeholder_item=True,
    has_history=True,
):
    """Text command decorator

    Text command signature: `text_command(editor, args)`
    `args` will be `None` in some contexts.
    The text view can be accessed with `editor.text_view`.

    :params *fields: Command parser fields.
    :param name: A name that can be typed in the command bar to invoke the
        command. Defaults to the decorated callable's `__name__`.
    :param is_enabled: A callable that returns a boolean value indicating if
        the command is enabled for the current context. By default a command
        is enabled if the current editor has a text view.
        Signature: `is_enabled(editor)`.
    :param lookup_with_parser: If True, use the `parser.parse` to
        lookup the command. The parser should return None if it receives
        a text string that cannot be parsed.
    :param has_placeholder_item: If True, add a placeholder item before
        other completions, which when accepted will execute the command.
        Other completions will add their value to the command without
        executing.
    :param has_history: Track and show history for this command if True
        (the default).
    """
    def command_decorator(func):
        func.name = name or func.__name__
        func.is_enabled = is_enabled or (lambda editor: True)
        func.create_parser = lambda editor: create_parser(func, fields, editor)
        func.lookup_with_parser = lookup_with_parser
        func.has_placeholder_item = has_placeholder_item
        func.has_history = has_history
        REGISTRY[func.name] = func
        return func
    return command_decorator


async def create_parser(command, fields, editor):
    parser = CommandParser(command, fields)
    return await parser.with_context(editor)


def set_context(args, **context):
    args.__context = Options(**context)


def get_context(args):
    return args.__context


class Incomplete(Exception):
    def __init__(self, *args, addchars=""):
        super().__init__(*args)
        self.addchars = addchars
