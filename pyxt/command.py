from .parser import CommandParser, Options

REGISTRY = {}


def command(
    name=None,
    parser=None,
    is_enabled=None,
    lookup_with_parser=False,
    has_placeholder_item=False,
):
    """Text command decorator

    Text command signature: `text_command(editor, args)`
    `args` will be `None` in some contexts.
    The text view can be accessed with `editor.text_view`.

    :param name: A name that can be typed in the command bar to invoke the
        command. Defaults to the decorated callable's `__name__`.
    :param parser: An object inplementing the `CommandParser` interface.
        Defaults to `CommandParser()`.
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
    """
    def command_decorator(func):
        async def arg_string(options):
            argstr = await func.parser.arg_string(options)
            if argstr:
                if not func.lookup_with_parser:
                    argstr = "{} {}".format(func.name, argstr)
                return argstr
            return func.name

        func.name = name[0] if name else func.__name__
        func.names = name or [func.__name__]
        nonlocal is_enabled
        if is_enabled is None:
            def is_enabled(editor):
                return editor is not None and editor.text_view is not None
        func.is_enabled = is_enabled
        func.parser = parser or CommandParser()
        func.lookup_with_parser = lookup_with_parser
        func.has_placeholder_item = has_placeholder_item
        func.arg_string = arg_string
        for name_ in func.names:
            REGISTRY[name_] = func
        return func

    if isinstance(name, str):
        name = name.split()
    return command_decorator


def set_context(args, **context):
    args.__context = Options(**context)


def get_context(args):
    return args.__context


class Incomplete(Exception):
    def __init__(self, *args, addchars=""):
        super().__init__(*args)
        self.addchars = addchars
