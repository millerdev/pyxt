from .parser import CommandParser

REGISTRY = {}


def command(
    name=None,
    parser=None,
    is_enabled=None,
    lookup_with_parser=False,
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
    """
    def command_decorator(func):
        def parse(argstr):
            if argstr.startswith(func.name + " "):
                argstr = argstr[len(func.name) + 1:]
            return func.parser.parse(argstr)

        def arg_string(options):
            argstr = func.parser.arg_string(options)
            if argstr:
                if not func.lookup_with_parser:
                    argstr = "{} {}".format(func.name, argstr)
                return argstr
            return func.name

        func.is_text_command = True
        func.name = name[0] if name else func.__name__
        func.names = name or [func.__name__]
        nonlocal is_enabled
        if is_enabled is None:
            def is_enabled(editor):
                return editor is not None and editor.text_view is not None
        func.is_enabled = is_enabled
        func.parser = parser or CommandParser()
        func.lookup_with_parser = lookup_with_parser
        func.parse = parse
        func.arg_string = arg_string
        for name_ in func.names:
            REGISTRY[name_] = func
        return func

    if isinstance(name, str):
        name = name.split()
    return command_decorator


class Incomplete(Exception):
    pass
