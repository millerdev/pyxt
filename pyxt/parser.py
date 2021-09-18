"""
Command parser specification:

- Arguments are space-delimited.
- Arguments must be in order.
- Argument names must be valid Python identifiers.
- Some examples:

    CommandParser(command, [
        Choice('selection all'),
        Choice(('forward', False), ('reverse', True), name='reverse'),
    ])
    matches:
        'selection reverse' : selection = 'selection',  reverse = True
        'sel rev'           : selection = 'selection',  reverse = True
        's r'               : selection = 'selection',  reverse = True
        'all reverse'       : selection = 'all',        reverse = True
        'a f'               : selection = 'all',        reverse = False
        ''                  : selection = 'selection',  reverse = False

    CommandParser(command, [
        Regex('regex'),
        Choice(('no-opt', False), ('opt', True), name='opt'),
        Int('num'),
    ])
    matches:
        '/^abc$/ opt 123'
        '/^abc$/ o 123'
        '/^abc$/o 123'

- An arguments may be skipped by entering an extra space:

    CommandParser(command, [
        Choice(('yes', True), ('no', False), name='bool'),
        Regex('regex'),
        Int('num', default=42),
    ])
    matches:
        'y'         : bool = True, regex = None, num = 42
        ' /abc/ 1'  : bool = None, regex = 'abc', num = 1
        ' /abc/'    : bool = None, regex = 'abc', num = None
        '  1'  : bool = False, regex = None, num = 1
"""
import asyncio
import os
import re
from inspect import iscoroutinefunction, signature, Parameter
from itertools import chain

from .util import user_path


class CommandParser:
    """Text command parser

    :params *argspec: Argument specifiers.
    """

    def __init__(self, command, argspec):
        self.command = command
        self.argspec = argspec
        # TODO assert no duplicate arg names

    def default_options(self):
        return Options(**{field.name: field.default for field in self.argspec})

    async def with_context(self, editor):
        """Get a new command parser with the given context

        See ``Field.with_context`` for argument specification.
        """
        argspec = [await arg.with_context(editor) for arg in self.argspec]
        return CommandParser(self.command, argspec)

    async def match(self, text, index=0):
        """Check if first argument can consume text at index

        :rtype: boolean
        """
        try:
            await self.argspec[0].consume(text, index)
        except (ParseError, ArgumentError):
            return False
        return True

    async def tokenize(self, text, index, args=None):
        """Generate a sequence of parsed arguments

        :param text: Argument string.
        :param index: Start tokenizing at this index in text.
        :param args: Optional object on which to set accumulated
        argument value attributes.
        :yields: A sequence of ``Arg`` objects. If there is leftover
        text after all arguments have been parsed the last generated
        arg will contain the remaining text with ``field = None``.
        """
        if args is None:
            args = Options()
        for field in self.argspec:
            arg = await Arg(field, text, index, args)
            if not arg.skipped:
                yield arg
                if not arg.errors:
                    index = arg.end
                    if index == len(text) and text[-1] != ' ':
                        index += 1
            setattr(args, field.name, arg)
        if index < len(text):
            yield await Arg(None, text, index, args)

    async def parse(self, text, index=0):
        """Parse arguments from the given text

        :param text: Argument string.
        :param index: Start parsing at this index in text.
        :raises: `ArgumentError` if the text string is invalid.
        :returns: `Options` object with argument values as attributes.
        """
        args = Options()
        errors = []
        async for arg in self.tokenize(text, index, args):
            if arg.field is None:
                if errors:
                    break
                msg = 'unexpected argument(s): ' + str(arg)
                raise ArgumentError(msg, args, [], arg.start)
            if not arg.errors:
                if errors:
                    del errors[:]
            else:
                errors.extend(arg.errors)
        if errors:
            msg = 'invalid arguments: {}'.format(text)
            raise ArgumentError(msg, args, errors)
        return Options(**{name: arg.value for name, arg in args})

    async def get_placeholder(self, text, index=0):
        """Get placeholder string to follow the given command text

        :param text: Argument string.
        :returns: A two-tuple of strings: `(args, hints)`.
        `args` is a string of entered arg values (or defaults).
        `hints` is a string of placeholder text, which can be used
        as a hint about remaining arguments to be entered.
        """
        args = []
        hints = []
        async for arg in self.tokenize(text, index):
            if arg.field is None or arg.errors:
                break
            value, hint = await arg.get_placeholder()
            if value:
                assert not hints, (text, hints, arg)
                args.append(value)
            if hint is None:
                break
            if hint:
                hints.append(hint)
            elif hints:
                raise NotImplementedError
        return " ".join(args), " ".join(hints)

    async def get_completions(self, text, index=0):
        """Get completions for the given command text

        :param text: Argument string.
        :param index: Index in ``text`` to start parsing.
        :returns: A list of possible values to complete the command.
        """
        async for arg in self.tokenize(text, index):
            if arg.field is None:
                return []
            if arg.could_consume_more:
                is_last_arg = arg.field is self.argspec[-1]
                # TODO what if arg has errors? is raw reliable?
                return await arg.get_completions(is_last_arg)
        return []

    def get_help(self, text):
        raise NotImplementedError

    async def arg_string(self, options, strip=True):
        """Compile command string from options

        :param options: Options object.
        :returns: Command argument string.
        :raises: Error
        """
        args = []
        if not self.command.lookup_with_parser:
            args.append(self.command.name)
        for field in self.argspec:
            try:
                value = getattr(options, field.name)
            except AttributeError:
                raise Error("missing option: {}".format(field.name))
            args.append(await field.arg_string(value))
        return " ".join(args).rstrip(" ") if strip else " ".join(args)


class Arg(object):
    """An argument parsed from a command string

    Important attributes:

    - `field` : Field that consumed this argument. Can be `None`.
    - `text` : Full command string.
    - `start` : Index of the first consumed character.
    - `end` : Index of the last consumed character.
    - `value` : Parsed argument value. Its type depends on `field`.
    - `skipped` : A boolean value indicating if this arg was skipped.
    - `errors` : Errors raised while consuming the argument.
    - `args` : `Options` object containing preceding Args.

    Arg objects are asynchronous, meaning they should be `await`ed after
    instantiation. However, in special circumstances it is not necessary
    to `await` them. For example, `await` is unnecessary if `field is None`.
    It is always safe to await a new arg, even if not strictly necessary.
    """

    def __init__(self, field, text, index, args):
        self.field = field
        self.text = text
        self.start = start = index
        self.skipped = False
        self.errors = []
        self.args = args
        if field is None:
            value = None
            index = len(text)
            assert index > start, (text, start, index)
        elif self.start > len(text):
            value = field.default
            index = start
        else:
            return  # await required for full initialization
        self._end_init(field, index, value)

    def __await__(self):
        return self._async_init(self.field, self.text, self.start).__await__()

    async def _async_init(self, field, text, start):
        if not hasattr(self, "end"):
            try:
                value, index = await field.consume(text, start)
            except ParseError as err:
                self.errors.append(err)
                value = field.default
                index = err.parse_index
            except ArgumentError as err:
                assert err.errors, "unexpected {!r}".format(err)
                self.errors.extend(err.errors)
                value = field.default
                index = err.errors[-1].parse_index
            self._end_init(field, index, value)
        return self

    def _end_init(self, field, index, value):
        self.end = index
        if field is not None:
            try:
                value = field.value_of(value, self)
            except SkipField:
                self.skipped = True
                value = self.field.default
        self.value = value

    def __repr__(self):
        if hasattr(self, "end"):
            plus = "+" if self.could_consume_more else ""
            return "<{} {!r}{}>".format(type(self).__name__, str(self), plus)
        return super().__repr__()

    def __str__(self):
        """Return the portion of the argument string consumed by this arg

        Does not include the space between this and the next arg even
        though that space is consumed by this arg.
        """
        return self.text[self.start:self.start + len(self)]

    def __len__(self):
        """Return the length of this arg in the command string

        Does not include the space between this and the next arg even
        though that space is consumed by this arg.
        """
        start, end = self.start, self.end
        if start == end:
            return 0
        if self.could_consume_more or self.text[end - 1:end] == " ":
            end -= 1
        assert start <= end, (self.text, start, end)
        return end - start

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value and str(self) == str(other)
        return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    @property
    def defaulted(self):
        return not self and self.end <= len(self.text)

    @property
    def could_consume_more(self):
        """Return true if this arg could consume more characters if present
        """
        return self.end > len(self.text)

    def consume_token(self, index=None):
        """Consume one space-delimited token from the command string

        This consumes all text up to (including) the next space in the
        command string. The returned value will not contain spaces. If
        the character at index is a space, then first element of the
        returned tuple will be `None` indicating that the argument
        should use its default value. This is meant to be called by
        subclasses; it is not part of the public interface.

        :param index: Optional index from which to consume; defaults to the
        start of this arg.
        :returns: A tuple `(<token>, <index>)` where `token` is the
        consumed string (`None` if there was nothing to consume), and
        `index` is that following the last consumed character.
        """
        if isinstance(self, Arg):
            text = self.text
            if index is None:
                index = self.start
        else:
            text = self
        if index > len(text):
            return None, index
        if index == len(text) or text[index] == ' ':
            return None, index + 1
        end = text.find(' ', index)
        if end < 0:
            token = text[index:]
            end = len(text)
        else:
            token = text[index:end]
        return token, end + 1

    async def get_placeholder(self):
        return await self.field.get_placeholder(self)

    async def get_completions(self, is_last_arg=None):
        def add_start(word, index):
            if getattr(word, 'start', None) is not None:
                word.start += index
            else:
                word = CompleteWord(word, start=index)
            word.is_last_arg = is_last_arg
            return word

        words = await self.field.get_completions(self)
        index = self.start
        for i, word in enumerate(words):
            if isinstance(word, dict):
                word["label"] = add_start(word["label"], index)
            else:
                words[i] = add_start(word, index)
        return words


IDENTIFIER_PATTERN = re.compile('^[a-zA-Z_][a-zA-Z0-9_]*$')


def identifier(name):
    ident = name.replace('-', '_')
    if not IDENTIFIER_PATTERN.match(ident):
        raise ValueError('invalid name: %s' % name)
    return ident


async def coro(value):
    return await value if asyncio.iscoroutine(value) else value


class Field(object):
    """Base command argument type used to parse argument values

    :param name: Argument name.
    :param default: Default value. If this is a callable it must accept
    one optional argument; it will be called with the editor to get the
    contextual default value for `with_context`.
    """

    def __init__(self, name, default=None):
        if not hasattr(self, 'args'):
            assert not hasattr(self, "kwargs"), type(self)
            self.args = [name]
            self.kwargs = {"default": default}
        if not hasattr(self, 'placeholder'):
            self.placeholder = name
        self.name = identifier(name)
        self.default = default

    def __eq__(self, other):
        if not issubclass(type(self), type(other)):
            return False
        return self.args == other.args

    def __str__(self):
        return self.placeholder

    def __repr__(self):
        sig = signature(self.__init__.__func__)
        defaults = {
            p.name: p.default
            for p in sig.parameters.values()
            if p.default is not Parameter.empty
        }
        NA = object()
        args = [repr(a) for a in self.args]
        args.extend(
            '{}={!r}'.format(k, v)
            for k, v in self.kwargs.items()
            if v != defaults.get(k, NA)
        )
        return '{}({})'.format(type(self).__name__, ', '.join(args))

    async def with_context(self, editor, **kwargs):
        """Return a Field instance with editor context

        The returned field object may be the same instance as the original
        on which this method was invoked.

        :param editor: The editor for which the command is being invoked.
        """
        if callable(self.kwargs.get("default")):
            kw = dict(self.kwargs)
            kw["default"] = await coro(kw["default"](editor))
            kw.update(kwargs)
            return type(self)(*self.args, **kw)
        return self

    async def consume(self, text, index):
        """Consume argument value from text starting at index

        This consumes the argument value plus a trailing space
        (if present).

        :param text: Text from which to consume argument value.
        :param index: Index into text from which to start consuming.
        :raises: ParseError if argument could not be consumed.
        :returns: A tuple `(<argument value>, <index>)` where `index` is
            that following the last consumed character in `text`.
            `index` is one more than the length of the given `text` if
            all remaining characters were consumed forming a valid token
            but the presence of any other character would extend the
            consumed token.
        """
        raise NotImplementedError("abstract method")

    def value_of(self, consumed, arg):
        """Convert consumed result to argument value

        :param consumed: The first item in the tuple returned by
        `self.consume(...)`.
        :param arg: The `Arg` object.
        :returns: The argument value.
        :raises: `SkipField` to cause this field to be skipped.
        """
        return consumed

    async def get_placeholder(self, arg):
        """Get placeholder string for this argument

        :param arg: An ``Arg`` object.
        :returns: A two-tuple: `(arg_string, placeholder)`. `arg_string`
        is either what has been typed, possibly with end delimiter
        added, or what could be typed to produce the default value for
        this argument. `placeholder` is a hint about what could be typed
        to populate the field. `placeholder` may be `None` if parsing
        cannot continue, for example, if the entered value is not valid.
        """
        hint = "" if arg else str(self)
        return "", hint

    async def get_completions(self, arg):
        """Get a list of possible completions for text

        :param arg: An ``Arg`` object.
        :returns: A list of possible completions for given arg.
        The ``start`` attribute of ``CompleteWord`` objects in the
        returned list may be set to an offset into the original
        token where the completion should start.
        """
        return []

    async def arg_string(self, value):
        """Convert parsed value to argument string"""
        raise NotImplementedError("abstract method")


class Choice(Field):
    """A multiple-choice argument type

    Choices are names without spaces. At least one choice name is
    required, more are usually provided.

    :param *choices: Two or more choice names or name/value pairs. Choices
    may be specified as a single space-delimited string, or one or more
    positional arguments consisting of either strings, or tuples in the
    form ("name-string", <value>). The value is the name in the case
    where name/value pairs are not given. The first choice is the
    default unless a `default=...` keyword argument is provided.
    :param name: Optional name, defaults to the first choice name. Must
    be specified as a keyword argument.
    """

    def __init__(self, *choices, **kw):
        self.args = choices
        self.kwargs = kw.copy()
        if len(choices) == 1 and isinstance(choices[0], str):
            choices = choices[0].split()
        if len(choices) < 2:
            raise ValueError('at least two choices are required')
        self.mapping = map = {}
        self.reverse_map = {}
        self.names = names = []
        self.alternates = alts = []
        for choice in choices:
            if isinstance(choice, str):
                if " " in choice:
                    name = choice
                    value = choice.split()[0]
                else:
                    name = value = choice
            else:
                try:
                    name, value = choice
                except (TypeError, ValueError):
                    raise ValueError("invalid choice: %r" % (choice,))
                if not isinstance(name, str):
                    raise ValueError("invalid choice name: %r" % (name,))
            for i, name in enumerate(name.split()):
                if i == 0:
                    names.append(name)
                    self.reverse_map[value] = name
                else:
                    alts.append(name)
                if name in map:
                    raise ValueError("ambiguous name: %r" % (name,))
                map[name] = value
                for i in range(1, len(name)):
                    key = name[:i]
                    if key in names or key in alts:
                        raise ValueError("ambiguous name: %r" % (key,))
                    if key in map:
                        map.pop(key)
                    else:
                        map[key] = value
        if "default" in kw:
            default = kw.pop("default")
            if iscoroutinefunction(default):
                default_value = map[names[0]]
            else:
                default_value = default() if callable(default) else default
            self.placeholder = self.reverse_map[default_value]
        else:
            default = map[names[0]]
            self.placeholder = names[0]
        super(Choice, self).__init__(kw.pop('name', names[0]), default)
        if kw:
            raise ValueError("unexpected arguments: %r" % (kw,))

    def __eq__(self, other):
        if not issubclass(type(self), type(other)):
            return False
        return self.args == other.args and self.kwargs == other.kwargs

    def __repr__(self):
        args = [repr(a) for a in self.args]
        args.extend('{}={!r}'.format(name, value)
                    for name, value in sorted(self.kwargs.items()))
        return '{}({})'.format(type(self).__name__, ', '.join(args))

    async def consume(self, text, index):
        """Consume a single choice name starting at index

        The token at index may be a complete choice name or a prefix
        that uniquely identifies a choice. Return the default (first)
        choice value if there is no token to consume.

        :returns: (<chosen or default value>, <index>)
        """
        token, end = Arg.consume_token(text, index)
        if token is None:
            return self.default, end
        if token in self.mapping:
            return self.mapping[token], end
        names = ', '.join(
            n for n in chain(self.names, self.alternates)
            if n.startswith(token)
        )
        if names:
            msg = '{!r} is ambiguous: {}'.format(token, names)
        else:
            end = index + len(token)
            names = ', '.join(self.names)
            msg = '{!r} does not match any of: {}'.format(token, names)
        raise ParseError(msg, self, index, end)

    async def get_placeholder(self, arg):
        if not arg:
            if arg.defaulted:
                return str(self), ""
            return "", str(self)
        names = await arg.get_completions()
        if len(names) == 1:
            return names[0], ""
        return "", None

    async def get_completions(self, arg):
        """List choice names that complete token"""
        token = str(arg)
        names = [n for n in self.names if n.startswith(token)]
        return names or [n for n in self.alternates if n.startswith(token)]

    async def arg_string(self, value):
        if value == self.default:
            return ""
        try:
            return self.reverse_map[value]
        except KeyError:
            raise Error("invalid value: {}={!r}".format(self.name, value))


class Int(Field):

    async def consume(self, text, index):
        """Consume an integer value

        :returns: (<int or default value>, <index>)
        """
        token, end = Arg.consume_token(text, index)
        if token is None:
            return self.default, end
        try:
            return int(token), end
        except (ValueError, TypeError) as err:
            raise ParseError(str(err), self, index, index + len(token))

    async def get_placeholder(self, arg):
        if not arg:
            if isinstance(self.default, int):
                if arg.defaulted:
                    return str(self.default), ""
                return "", str(self.default)
            return "", str(self)
        return str(arg), ""

    async def arg_string(self, value):
        if value == self.default:
            return ""
        if isinstance(value, int):
            return str(value)
        raise Error("invalid value: {}={!r}".format(self.name, value))


class Float(Int):
    """A float argument
    """

    async def consume(self, text, index):
        """Consume a float value

        :returns: (<float or default value>, <index>)
        """
        token, end = Arg.consume_token(text, index)
        if token is None:
            return self.default, end
        try:
            return float(token), end
        except (ValueError, TypeError) as err:
            raise ParseError(str(err), self, index, index + len(token))

    async def get_placeholder(self, arg):
        if not arg:
            if isinstance(self.default, float):
                if arg.defaulted:
                    return str(self.default), ""
                return "", str(self.default)
            return "", str(self)
        return str(arg), ""

    async def arg_string(self, value):
        if value == self.default:
            return ""
        if isinstance(value, float):
            return str(value)
        raise Error("invalid value: {}={!r}".format(self.name, value))


class String(Field):

    ESCAPES = {
        '\\': '\\',
        "'": "'",
        '"': '"',
        'a': '\a',
        'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t',
        'v': '\v',
    }
    DELIMITERS = '"\''

    async def consume(self, text, index):
        """Consume a string value

        :returns: (<string or default value>, <index>)
        """
        if index >= len(text):
            if index == len(text):
                index += 1
            return self.default, index
        escapes = self.ESCAPES
        if text[index] not in self.DELIMITERS:
            delim = ' '
            start = index
            escapes = escapes.copy()
            escapes[' '] = ' '
        else:
            delim = text[index]
            start = index + 1
        chars, esc = [], 0
        for i, c in enumerate(text[start:], start=start):
            if esc:
                esc = 0
                try:
                    chars.append(escapes[c])
                    continue
                except KeyError:
                    chars.append('\\')
            elif c == delim:
                if delim == ' ':
                    if not chars:
                        return self.default, i + 1
                elif text[i + 1:i + 2] == ' ':
                    i += 1  # consume trailing space
                return ''.join(chars), i + 1
            if c == '\\':
                esc = 1
            else:
                chars.append(c)
        if not esc:
            return ''.join(chars), len(text) + 1
        if delim == ' ':
            delim = ''
        msg = 'unterminated string: {}{}'.format(delim, text[start:])
        raise ParseError(msg, self, index, len(text))

    async def arg_string(self, value):
        if value == self.default:
            return ""
        if not isinstance(value, str):
            raise Error("invalid value: {}={!r}".format(self.name, value))
        value = value.replace("\\", "\\\\")
        for char, esc in self.ESCAPES.items():
            if esc in value and esc not in "\"\\'":
                value = value.replace(esc, "\\" + char)
        return delimit(value, "\"'")[0]

    async def get_placeholder(self, arg):
        if not arg:
            if isinstance(self.default, str):
                value = delimit(self.default, self.DELIMITERS)[0]
                if arg.defaulted:
                    return value, ""
                return "", value
            return await super().get_placeholder(arg)
        first = str(arg)[0]
        needs_delim = arg.could_consume_more and first in self.DELIMITERS
        delim = first if needs_delim else ""
        return str(arg) + delim, ""


class UnlimitedString(String):

    async def consume(self, text, index):
        """Consume string value to the end of text

        :returns: (<string or default value>, <index>)
        """
        if index >= len(text):
            if index == len(text):
                index += 1
            return self.default, index
        return text[index:], len(text) + 1

    async def arg_string(self, value):
        if value == self.default:
            return ""
        if not isinstance(value, str):
            raise Error("invalid value: {}={!r}".format(self.name, value))
        return value

    async def get_placeholder(self, arg):
        if not arg:
            if isinstance(self.default, str):
                if arg.defaulted:
                    return self.default, ""
                return "", self.default
            return "", str(self)
        return str(arg), ""


class File(String):
    """File path field

    :param name: Argument name.
    :param directory: If true, browse directories only. Default false.
    """

    def __init__(self, name, directory=False, default=None, _editor=None):
        self.args = [name]
        self.kwargs = {"directory": directory, "default": default}
        self.directory = directory
        self.editor = _editor
        super().__init__(name, default=default)

    async def with_context(self, editor):
        default = self.kwargs["default"]
        if callable(default):
            default = await coro(default(editor))
        return type(self)(
            self.name,
            directory=self.directory,
            default=default,
            _editor=editor,
        )

    @property
    async def path(self):
        if self.editor is None:
            return None
        return await self.editor.dirname

    @property
    async def project_path(self):
        if self.editor is None:
            return None
        return await self.editor.project_path

    @staticmethod
    def relative(path):
        if os.path.isabs(path):
            return path.lstrip("/").lstrip(os.path.sep)
        return path

    async def consume(self, text, index):
        """Consume a file path

        :returns: (<path>, <index>)
        """
        path, stop = await super().consume(text, index)
        if path is None:
            return path, stop
        if path.startswith('~'):
            path = os.path.expanduser(path)
        elif path.startswith("..."):
            project_path = await self.project_path
            if path == '...':
                path = project_path
            elif path.startswith('.../'):
                path = os.path.join(project_path, self.relative(path[4:]))
        basepath = await self.path
        if os.path.isabs(path) or basepath is None:
            return path, stop
        return os.path.join(basepath, path), stop

    async def get_completions(self, arg):
        from os.path import exists, expanduser, isabs, isdir, join, realpath, sep, split
        if arg.start >= len(arg.text):
            token = ""
        else:
            token = (await super().consume(arg.text, arg.start))[0] or ""
        if token == '~':
            return [CompleteWord('~/', (lambda:''))]
        if token == '...' and await self.project_path:
            return [CompleteWord('.../', (lambda:''))]
        if token.startswith('~'):
            path = expanduser(token)
        elif token.startswith('.../'):
            project_path = await self.project_path
            if project_path and isabs(project_path):
                path = join(project_path, self.relative(token[4:]))
            else:
                path = token
        else:
            path = token
        if not isabs(path):
            if await self.path is None:
                return []
            else:
                path = join(realpath(await self.path), path)
        root, name = split(path)
        if not exists(root):
            return []
        if name == token:
            start = 0
        else:
            if name:
                assert token.endswith(name), (token, name)
                token_dir = token[:-len(name)]
            else:
                token_dir = token
            start = sum(2 if c == ' ' else 1 for c in token_dir)

        def delim(word):
            def escape(word):
                return word.replace(' ', '\\ ')

            def get_delimiter():
                return "" if dirsep else " "

            dirsep = sep if self.directory or isdir(join(root, word)) else ""
            return CompleteWord(word + dirsep, get_delimiter, start, escape)

        if not name:
            def match(n):
                return not n.startswith(".")
        elif name.islower():
            def match(n, name=name.lower()):
                return n.lower().startswith(name)
        else:
            # edge case: when first match begins with a capital letter and
            # user types that letter then TAB ... typed letter is converted
            # to upper-case, which switches to the other matcher
            def match(n):
                return n.startswith(name)

        if self.directory:
            names = next(os.walk(root))[1]
        else:
            names = os.listdir(root)
        names = [delim(n) for n in sorted(names, key=str.lower) if match(n)]
        if isdir(path) and (name == ".." or name in names):
            if name in names:
                names.remove(name)
            names.append(delim(name))
        return CompletionsList(names, title=user_path(root))

    async def get_placeholder(self, arg):
        if not arg:
            if isinstance(self.default, str):
                if arg.defaulted:
                    return user_path(self.default), ""
                return "", user_path(self.default)
            path = await self.path
            if path:
                return "", user_path(path)
        return await super().get_placeholder(arg)

    async def arg_string(self, value):
        if value and not self.directory and value.endswith((os.path.sep, "/")):
            raise Error("not a file: {}={!r}".format(self.name, value))
        path = await self.path
        if path and value.startswith(os.path.join(path, "")):
            value = value[len(path) + 1:]
        else:
            home = os.path.expanduser("~/")
            if value.startswith(home):
                value = "~/" + value[len(home):]
        return await super().arg_string(value)


class DynamicList(String):

    def __init__(self, name, get_items, name_attribute, default=None, _editor=None):
        self.args = [name]
        self.kwargs = {
            "get_items": get_items,
            "name_attribute": name_attribute,
            "default": default,
        }
        self.get_items = get_items
        self.name_attribute = name_attribute
        self.editor = _editor
        super().__init__(name, default=default)

    async def with_context(self, editor):
        field = await super().with_context(editor, _editor=editor)
        if not hasattr(self, "editor") or field.editor is not None:
            return field
        return type(self)(*self.args, _editor=editor, **self.kwargs)

    def iteritems(self):
        if isinstance(self.name_attribute, str):
            def nameof(item):
                return getattr(item, self.name_attribute)
        else:
            nameof = self.name_attribute
        return ((nameof(item), item) for item in self.get_items(self.editor))

    async def consume(self, text, index):
        token, end = await super().consume(text, index)
        if token is self.default:
            return token, end
        items = list(self.iteritems())
        if isinstance(token, str):
            ltok = str(token).lower()
            comps = [(name, item)
                     for name, item in items
                     if name.lower().startswith(ltok)]
            if comps:
                return comps[0][1], end
        end = index + len(token)
        names = ', '.join(name for name, item in items)
        msg = '{!r} does not match any of: {}'.format(token, names)
        raise ParseError(msg, self, index, end)

    async def get_completions(self, arg, escape=lambda n: n.replace(" ", "\\ ")):
        token = str(arg).lower()
        names = (name for name, item in self.iteritems())
        return [escape(n) for n in names if n.lower().startswith(token)]

    async def get_placeholder(self, arg):
        if not arg:
            if arg.defaulted:
                if isinstance(self.default, str):
                    return self.default, ""
                return "", None
            default = str(self.default) if self.default is not None else ""
            hint = default if default else str(self)
            return "", hint
        token = str(arg)
        comps = await self.get_completions(token, lambda n: n)
        if comps:
            return comps[0], ""
        return "", None


class RegexPattern(str):

    __slots__ = ["_flags"]
    DEFAULT_FLAGS = re.UNICODE | re.MULTILINE

    def __new__(cls, value="", flags=0, default_flags=DEFAULT_FLAGS):
        obj = super(RegexPattern, cls).__new__(cls, value)
        obj._flags = flags | default_flags
        return obj

    @property
    def flags(self):
        return self._flags

    def __hash__(self):
        return super(RegexPattern, self).__hash__() ^ hash(self._flags)

    def __repr__(self):
        return super(RegexPattern, self).__repr__() + Regex.repr_flags(self)

    def __eq__(self, other):
        streq = super(RegexPattern, self).__eq__(other)
        if streq and isinstance(other, RegexPattern):
            return self.flags == other.flags
        return streq

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        strlt = super(RegexPattern, self).__lt__(other)
        if not strlt and isinstance(other, RegexPattern) \
                and super(RegexPattern, self).__eq__(other):
            return self.flags < other.flags
        return strlt

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other


class Regex(Field):

    DELIMITERS = "/:\"'"

    def __init__(self, name, replace=False, default=None, flags=0, delimiters=DELIMITERS):
        self.args = [name]
        self.kwargs = {
            "replace": replace,
            "default": default,
            "flags": flags,
            "delimiters": delimiters,
        }
        self.replace = replace
        self.flags = flags
        self.delimiters = delimiters
        default = (None, None) if replace and default is None else default
        if isinstance(default, str):
            self.placeholder = delimit(default, delimiters, always=replace)[0]
            default = RegexPattern(default, flags)
        super(Regex, self).__init__(name, default)

    async def consume(self, text, index, _default=None):
        """Consume regular expression and optional replacement string and flags

        :returns: (<value>, <index>) where value is one of the following:
            replace     value
            False       <RegexPattern>
            True        (<RegexPattern>, <replacement string>)
        Either <RegexPattern> or <replacement string> may be the
        respective portion of the default value if not present.
        """
        if index > len(text):
            return self.default, index
        if index == len(text) or text[index] == ' ':
            return self.default, index + 1
        if self.replace and text[index] not in self.delimiters:
            msg = "invalid search pattern: {!r}".format(text[index:])
            raise ParseError(msg, self, index, index)
        expr, index = self.consume_expression(text, index)
        if self.replace:
            if _default is None:
                _default = self.default
            if index > len(text):
                index = len(text) + 1  # to show we would consume more
                return (RegexPattern(expr, self.flags), _default[1]), index
            repl, index = self.consume_expression(text, index - 1)
            flags, index = self.consume_flags(text, index)
            return (RegexPattern(expr, flags), repl), index
        flags, index = self.consume_flags(text, index)
        return RegexPattern(expr, flags), index

    def consume_expression(self, text, index):
        start = index
        if self.replace or text[index] in self.delimiters:
            delim = text[index]
            start += 1
        else:
            delim = ' '
        chars, esc = [], 0
        i = start
        for i, c in enumerate(text[start:], start=start):
            if esc:
                esc = 0
                chars.append(c)
                continue
            elif c == delim:
                return ''.join(chars), i + (1 if delim != ' ' else 0)
            chars.append(c)
            if c == '\\':
                esc = 1
        if not esc:
            return ''.join(chars), len(text) + 1
        token = ''.join(chars)
        msg = 'unterminated regex: {}{}'.format(delim, token)
        raise ParseError(msg, self, index, len(text) + 1)

    def consume_flags(self, text, index):
        flags = {'i': re.IGNORECASE, 's': re.DOTALL, 'l': re.LOCALE}
        value = self.flags
        for i, char in enumerate(text[index:], start=index):
            if char in flags:
                value |= flags[char]
            elif char == ' ':
                return value, i + 1
            else:
                msg = 'unknown flag: {}'.format(char)
                raise ParseError(msg, self, index, i)
        return value, len(text) + 1

    async def get_placeholder(self, arg):
        if not arg:
            if arg.defaulted:
                if self.replace:
                    if all(isinstance(v, str) for v in self.default):
                        find, replace = self.default
                        value, delim = delimit(find, self.delimiters)
                        return "".join([value, replace, delim]), ""
                    return "", None
                if isinstance(self.default, str):
                    value = delimit(self.default, self.delimiters)[0]
                    return value, ""
                return "", None
            return "", str(self)
        text = arg.text
        index = arg.start
        delim = text[index] if text[index] in self.delimiters else ""
        if self.replace and not delim:
            msg = "invalid search pattern: {!r}".format(text[index:])
            raise ParseError(msg, self, index, index)
        value, index = self.consume_expression(text, index)
        value = delim + value
        if self.replace:
            if index > len(text):
                return value + delim * 2, ""
            replace, index = self.consume_expression(text, index - 1)
            value += delim + replace
        end = delim if index >= len(text) else ""
        return value + end, ""

    @classmethod
    def repr_flags(cls, value):
        if not value.flags:
            return ""
        chars = []
        if value.flags & re.IGNORECASE:
            chars.append("i")
        if value.flags & re.DOTALL:
            chars.append("s")
        if value.flags & re.LOCALE:
            chars.append("l")
        return "".join(chars)

    async def arg_string(self, value):
        if value == self.default:
            return ""
        if self.replace:
            if not (isinstance(value, (tuple, list)) and len(value) == 2):
                raise Error("invalid value: {}={!r}".format(self.name, value))
            find, replace = value
            if not isinstance(replace, str):
                raise Error("invalid value: {}={!r}".format(self.name, value))
            allchars = find + replace
        else:
            replace = None
            allchars = find = value
        if not isinstance(find, RegexPattern):
            raise Error("invalid value: {}={!r}".format(self.name, value))
        pattern, delim = delimit(find, self.delimiters, allchars, self.replace)
        if self.replace:
            if delim in replace:
                replace = escape(replace, delim)
            pattern += replace + delim
        return pattern + self.repr_flags(find)


def delimit(value, delimiters, allchars=None, always=False):
    """Add delimiters before and after (escaped) value if necessary

    :param value: String to delimit.
    :param delimiters: A sequence of possible delimiters.
    :param allchars: Characters to consider when choosing delimiter.
    Defaults to `value`.
    :param always: Always add delimiters, even when not required.
    :returns: (<delimited value>, delimiter)
    """
    def should_delimit(value):
        return (
            always or
            not value or
            " " in value or
            any(value.startswith(c) for c in delimiters) or
            (hasattr(value, "flags") and Regex.repr_flags(value))
        )

    if allchars is None:
        allchars = value
    if not should_delimit(value):
        return value, ''
    delims = []
    for i, delim in enumerate(delimiters):
        count = allchars.count(delim)
        if not count:
            break
        delims.append((count, i, delim))
    else:
        delim = min(delims)[2]
        value = escape(value, delim)
    return "".join([delim, value, delim]), delim


def escape(value, delimiter):
    """Escape delimiters in value"""
    return re.subn(
        r"""
        (
            (?:
                \A          # beginning of string
                |           # or
                [^\\]       # not a backslash
                |           # or
                (?<={0})    # boundary after previous delimiter
            )
            (?:\\\\)*       # exactly 0, 2, 4, ... backslashes
        )
        {0}                 # delimiter
        """.format(delimiter),
        r"\1\\" + delimiter,
        value,
        flags=re.UNICODE | re.VERBOSE,
    )[0]


class VarArgs(Field):
    """Argument type that consumes a variable number of arguments

    :param name: Name of the list of consumed arguments.
    :param field: A field to be consumed a variable number of times.
    :param min: Minimum number of times to consume field (default is 1).
    :param placeholder:
    :param default: The default value if there are no arguments to consume.
    If this is callable it will be called with no arguments to create a value
    each time the default value is needed.
    PROPOSED: `field` may be a list of fields in which case the result of this
    VarArgs field will be a list of dicts. Are they all required?
    """

    def __init__(self, name, field, *, min=1, placeholder=None, default=list):
        self.args = [name, field]
        self.kwargs = {"min": min, "placeholder": placeholder, "default": default}
        super().__init__(name, default=default)
        self.field = field
        self.min = min
        self.placeholder = placeholder

    @property
    def default(self):
        return self._default() if callable(self._default) else self._default

    @default.setter
    def default(self, value):
        self._default = value

    def __str__(self):
        if self.placeholder is None:
            return "{} ...".format(self.field.name)
        return self.placeholder

    async def with_context(self, *args, **kw):
        field = await self.field.with_context(*args, **kw)
        return VarArgs(self.name, field, **self.kwargs)

    async def consume(self, text, index):
        values = []
        if index >= len(text):
            value, index = await self.field.consume(text, index)
            values.append(value)
        else:
            while index < len(text):
                value, index = await self.field.consume(text, index)
                values.append(value)
        if len(values) < self.min:
            raise Error("not enough arguments (found {}, expected {})".format(
                        len(values), self.min))
        return values, index

    async def get_placeholder(self, arg):
        text = arg.text
        index = arg.start
        start = hint = None
        values = []
        while index != start:
            start = index
            sub = await Arg(self.field, text, index, arg.args)
            value, hint = await sub.get_placeholder()
            if value:
                assert not hint, (self, arg, value, hint)
                values.append(value)
            if hint or index > len(text) or hint is None:
                break
            if sub.errors:
                return "", None
            index = sub.end
        if hint is None:
            return "", None
        value = " ".join(values)
        placeholder = "..." if self.placeholder is None else self.placeholder
        return value, (placeholder if value else f"{hint} {placeholder}")

    async def get_completions(self, arg):
        index = arg.start
        while True:
            sub = await Arg(self.field, arg.text, index, arg.args)
            if sub.could_consume_more:
                words = await self.field.get_completions(sub)
                if index > arg.start:
                    diff = index - arg.start
                    for i, word in enumerate(words):
                        if getattr(word, 'start', None) is not None:
                            word.start += diff
                        else:
                            words[i] = CompleteWord(word, start=diff)
                return words
            if sub.errors or sub.end == index:
                break
            index = sub.end
        return []

    async def arg_string(self, value):
        return " ".join([await self.field.arg_string(v) for v in value])


class SubParser(Field):
    """Dispatch to a named group of sub arguments

    The first argument consumed by this SubParser is used to lookup a
    SubArgs instance by name, and remaining arguments are parsed using
    the SubArgs.

    :param name: Name of sub-parser result.
    :param *subargs: One or more SubArgs objects containing more
    arguments to be parsed.
    """

    def __init__(self, name, *subargs):
        self.args = (name,) + subargs
        self.kwargs = {}
        super(SubParser, self).__init__(name)
        self.subargs = {p.name: p for p in subargs}

    async def with_context(self, editor):
        subs = [await a.with_context(editor)
                for a in self.args[1:]
                if a.is_enabled(editor)]
        return SubParser(self.name, *subs)

    async def consume(self, text, index):
        """Consume arguments based on the name of the first argument

        :returns: ((subparser, <consumed argument options>), <index>)
        :raises: ParserError, ArgumentError with sub-errors
        """
        name, end = Arg.consume_token(text, index)
        if not name:
            # TODO resolve difference with get_placeholder (get first arg defaults)
            return self.default, end
        sub = self.subargs.get(name)
        if sub is None:
            names = [n for n in self.subargs if n.startswith(name)]
            if len(names) != 1:
                if len(names) > 1:
                    msg = "{!r} is ambiguous: {}".format(
                        name, ", ".join(sorted(self.subargs))
                    )
                else:
                    msg = "{!r} does not match any of: {}".format(
                        name, ", ".join(sorted(self.subargs))
                    )
                    end = index + len(name)
                raise ParseError(msg, self, index, end)
            sub = self.subargs[names[0]]
        opts, index = await sub.parse(text, end)
        return (sub, opts), index

    async def get_placeholder(self, arg):
        if not arg:
            if arg.defaulted:
                name, sub = next(iter(self.subargs.items()))
                value, hint = await sub.get_placeholder(arg)
                assert not hint, (arg, arg.field, arg.text, value, hint)
                return " ".join([name, value]), ""
            return "", "{} ...".format(self)
        text = arg.text
        name, end = arg.consume_token()
        space_after_name = end < len(text) or text[arg.start:end].endswith(" ")
        if name is None:
            if space_after_name:
                raise NotImplementedError
                return "", str(self)
            return "", "{} ...".format(self)
        sub = self.subargs.get(name)
        if sub is None:
            names = [n for n in self.subargs if n.startswith(name)]
            if not names:
                return "", None
            if len(names) > 1:
                if space_after_name:
                    return "", None
                return "", "..."
            sub = self.subargs[names[0]]
            value = names[0]
        else:
            value = name
        values = [value]
        sub_value, hint = await sub.parser.get_placeholder(text, end)
        if hint is None:
            return ("", None)
        if sub_value:
            values.append(sub_value)
        return " ".join(values), hint

    async def get_completions(self, arg):
        text = arg.text
        name, end = arg.consume_token()
        if name is None:
            assert end >= len(text), (arg, text)
            return sorted(self.subargs)
        if end > len(text):
            # there is no space after name
            return [w for w in sorted(self.subargs) if w.startswith(name)]
        sub = self.subargs.get(name)
        if sub is None:
            names = [n for n in self.subargs if n.startswith(name)]
            if len(names) != 1:
                return []
            sub = self.subargs[names[0]]
        words = await sub.parser.get_completions(text, end)
        for word in words:
            word.start -= arg.start
        return words

    async def arg_string(self, value):
        sub, opts = value
        return sub.name + " " + await sub.parser.arg_string(opts, strip=False)


class SubArgs(object):
    """Arguments and data for SubParser"""

    def __init__(self, name, *argspec, is_enabled=None, **data):
        self.name = name
        self.data = data
        self._is_enabled = is_enabled
        command = Options(lookup_with_parser=True)
        self.parser = CommandParser(command, argspec)

    def is_enabled(self, editor):
        if self._is_enabled is not None:
            return self._is_enabled(editor)
        return editor is not None and editor.text_view is not None

    async def with_context(self, editor):
        sub = super(SubArgs, SubArgs).__new__(SubArgs)
        sub.name = self.name
        sub.data = self.data
        sub._is_enabled = self._is_enabled
        sub.parser = await self.parser.with_context(editor)
        return sub

    async def parse(self, text, index):
        args = Options()
        errors = []
        async for arg in self.parser.tokenize(text, index, args):
            if arg.field is None:
                index = arg.start
                break
            if arg.errors:
                errors.extend(arg.errors)
                if arg.could_consume_more:
                    break
            else:
                index = arg.end
        if errors:
            msg = 'invalid arguments: {}'.format(text)
            raise ArgumentError(msg, args, errors, index)
        return Options(**{name: arg.value for name, arg in args}), index

    async def get_placeholder(self, arg):
        if arg.defaulted:
            values = []
            for field in self.parser.argspec:
                value, hint = await field.get_placeholder(arg)
                if hint:
                    raise NotImplementedError
                if hint is None:
                    return value, hint
                values.append(value)
            return " ".join(values), ""
        raise NotImplementedError

    def __repr__(self):
        args = [repr(self.name)]
        args.extend(repr(a) for a in self.parser.argspec)
        if self._is_enabled is not None:
            args.append("is_enabled={!r}".format(self._is_enabled))
        args.extend("{}={!r}".format(*kv) for kv in sorted(self.data.items()))
        return "{}({})".format(type(self).__name__, ", ".join(args))


class Conditional(Field):

    def __init__(self, is_enabled, field, editor=None, **kw):
        default = kw.pop('default', field.default)
        self.args = [is_enabled, field, default]
        super().__init__(field.name, default, **kw)
        self.is_enabled = is_enabled
        self.field = field
        self.editor = editor

    async def with_context(self, editor):
        field = await self.field.with_context(editor)
        return type(self)(self.is_enabled, field, editor, default=self.default)

    async def consume(self, text, index):
        return await self.field.consume(text, index)

    def value_of(self, consumed, arg):
        if not self.is_enabled(arg):
            raise SkipField(self.default)
        return self.field.value_of(consumed, arg)

    async def get_placeholder(self, arg):
        return await self.field.get_placeholder(arg)

    async def get_completions(self, arg):
        return await self.field.get_completions(arg)

    async def arg_string(self, value):
        return await self.field.arg_string(value)


class Options(object):
    """Parsed argument container

    Options are stored as attributes. Attribute names containing a double-
    underscore (__) are considered to be private and are excluded from
    operations that affect option values.
    """

    # DEFAULTS = <dict of defaults> # optional attribute for subclasses

    def __init__(self, **opts):
        if hasattr(self, "DEFAULTS"):
            for name, value in self.DEFAULTS.items():
                if name not in opts:
                    setattr(self, name, value)
        for name, value in list(opts.items()):
            setattr(self, name, value)

    def __eq__(self, other):
        return issubclass(type(other), Options) and dict(self) == dict(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        obj = Options().__dict__
        return ((k, v)
            for k, v in self.__dict__.items()
            if k not in obj and "__" not in k)

    def __len__(self):
        return len(list(self.__iter__()))

    def __repr__(self):
        def line_repr(obj):
            rep = repr(obj)
            if '\n' in rep:
                rep = rep.replace('\n', ' ')
            return rep
        vars = ['{}={}'.format(k, line_repr(v)) for k, v in self]
        return '{}({})'.format(type(self).__name__, ', '.join(vars))


class CompleteWord(str):

    def __new__(cls, _value="", get_delimiter=None, start=None, escape=None, **kw):
        obj = super(CompleteWord, cls).__new__(cls, _value)
        if isinstance(_value, CompleteWord):
            if get_delimiter is None:
                get_delimiter = _value.get_delimiter
            if start is None:
                start = _value.start
            if escape is None:
                escape = _value.escape
            for key, value in _value.__dict__.items():
                if not key.startswith("_") and key not in kw:
                    setattr(obj, key, value)
        obj.get_delimiter = get_delimiter or (lambda: " ")
        obj.start = start
        obj.escape = escape or (lambda v: v)
        obj.__dict__.update(kw)
        return obj

    def complete(self):
        return self.escape(self) + self.get_delimiter()


class CompletionsList(list):

    __slots__ = ["title", "offset"]

    def __init__(self, *args, title=None):
        super().__init__(*args)
        self.title = title


class Error(Exception):

    def __str__(self):
        return self.args[0]

    def __eq__(self, other):
        if not issubclass(type(other), type(self)):
            return False
        return self.args == other.args

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self)


class ArgumentError(Error):

    def __str__(self):
        ext = ""
        if self.errors:
            ext = "\n" + "\n".join(str(err) for err in self.errors)
        return self.args[0] + ext

    @property
    def options(self):
        return self.args[1]

    @property
    def errors(self):
        return self.args[2]

    @property
    def parse_index(self):
        return self.args[3]


class ParseError(Error):

    @property
    def arg(self):
        return self.args[1]

    @property
    def error_index(self):
        return self.args[2]

    @property
    def parse_index(self):
        return self.args[3]


class SkipField(Error):

    @property
    def value(self):
        return self.args[0]
