# PyXT: Python eXTensions for VS Code

## Installation and setup

- Install the extension in VS Code
- Setup a virtualenv with Python 3.7+
  ```sh
  python3 -m venv /path/to/your/virtualenv  # or your preferred way to create a virtualenv
  ```
- Install requirements in the virtualenv (you may prefer to use the tag of the
  version being installed rather than `master`)
  ```sh
  /path/to/your/virtualenv/bin/pip install -r \
    https://github.com/millerdev/PyXT/raw/master/requirements.txt
  ```
- Open Settings in VS Code and search for `pyxt.pythonPath`. Set the value to
  the path of the `python` executable in the virtualenv created above. It will
  be something like `/path/to/your/virtualenv/bin/python`.

## Usage

Type Ctrl+Shift+P and select _PyXT: Command_ to open the PyXT command bar.

Most commands may also be invoked directly as VS Code commands (e.g.,
_PyXT: Open File_), and may be assigned a keyboard shortcut.

## Commands

- `ag MATCH PATH OPTIONS...` - [The Silver Searcher](https://github.com/ggreer/the_silver_searcher) code
  search. Ag must be installed separately.  
  VS Code command: _PyXT: Ag (The Silver Searcher)_.
- `argwrap` - Wrap/unwrap function or collection arguments based on the current
  selection. Wrap if a single line is selected, otherwise unwrap. For nested
  function calls or collections, place the cursor inside the delimited region to
  be wrapped.  
  VS Code command: _PyXT: ArgWrap_.
- `history ACTION COMMAND` - redo most recent command or clear command history.
- `isort FIRSTPARTY SELECTION` - [isort](https://pycqa.github.io/isort/) your
  imports so you don't have to. Sort selection or entire file. `FIRSTPARTY` is a
  comma-delimited list of known first-party packages. `SELECTION` controls
  whether to sort the selection or the entire file; it can usually be ignored
  because it defaults to `selection` if there is one and `all` otherwise.  
  VS Code command: _PyXT: isort_.
- `open FILE_PATH` - Open files by path with auto-complete. The entered path is relative to
  the location of the active text editor's file by default. It may also start
  with `~` (home directory prefix). Absolute paths are supported as well.  
  VS Code command: _PyXT: Open File_.
- `python EXECUTABLE SCOPE OPTIONS...` - Run selected text or entire file
  (depending on `SCOPE`) with the given Python `EXECUTABLE` (or virtualenv) and
  show the result, which consists of printed output plus non-null result of the
  final expression. Accept (by pressing Enter) the result to copy it to the
  clipboard.  
  VS Code command: _PyXT: Python_
- `rename FILENAME` - Rename the active editor's file. `FILENAME` is a file
  name or path. If the name or path of an existing file is provided, it will be
  overwritten with the active editor's content. If a directory name is given,
  the active file will be moved into that directory.  
  VS Code Command: _PyXT: Rename_.
- `replace PATTERN RANGE SEARCH_TYPE` - Find and replace text in the active
  editor. `PATTERN` is a find/replace pattern in the form `/find/replace/flags`
  where `find` is a regex or literal (depending on `SEARCH_TYPE`), `replace` is
  a replacement pattern, and `flags` are optional regular expression flags.
  Supported flags are `i` (ignore case) and `s` (dot matches any character,
  including newline).  
  VS Code Command: _PyXT: Replace_.

The command name should not be typed when it is invoked directly via its
VS Code command (rather than with the PyXT Command bar). In this case, simply
enter arguments as required.

### Command Syntax

Command arguments must be separated by spaces in the command bar. Auto-complete
suggestions will be provided as the command is entered.

_Important:_ white space is significant! Example: a command accepting multiple
arguments might be entered as:

```
ag match_first ~/path/second -i --after 3
```

The default value of an argument may be selected by omitting its value and
typing a space to advance to the next argument:

```
ag  ~/path/second -i --after 3
```

Note the two spaces between `ag` and `~/path/second`. In the case of `ag`, the
first argument defaults to the selected text in the active text editor.

Arguments containing spaces may be enclosed in quotes. Alternately spaces may
be escaped with a backslash prefix (e.g., `\ `).

Commands will often provide contextual argument hints as the first item in the
list of quick-pick suggestions. Accepting this suggestion will invoke the
command with default values as shown.

### Keybindings

Keybindings may be assigned to any PyXT command having a corresponding VS Code
command. These commands may also be invoked directly via the Command Palette.
Additionally keybindings may be added for custom commands.

#### Example keybindings.json entries

_Ctrl+Shift+A O_ to open command bar with text: `open /my/favorite/directory/`

```json
{
  "key": "ctrl+shift+a o",
  "command": "pyxt.command",
  "args": {"text": "open /my/favorite/directory/"}
}
```

_Ctrl+Shift+A D_ to immediately execute the command: `ag 'hot search'`

```json
{
  "key": "ctrl+shift+a g",
  "command": "pyxt.command",
  "args": {"text": "ag 'hot search'", "exec": true}
}
```

### Adding your own custom commands

Adding a new PyXT command is as simple as writing a Python module and loading
it as a "user script." Here is a very simple "hello world" example to get
started:

```py
from pyxt.command import command
from pyxt.parser import String
from pyxt.results import result

@command(String("name", default="world"))
async def hello(editor, args):
    return result([f"Hello {args.name}!"])
```

Save the script in a file, and set the `pyxt.userScript` setting in VS Code.
Then reload VS Code and open the _PyXT: Command_ bar to run the new command.
VS Code must be reloaded (_Developer: Reload Window_) or restarted to register
changes if the user script is modified.

The value of `pyxt.userScript` may be one of the following:

- absolute path
- user path accepted by [`expanduser()`](https://docs.python.org/3/library/os.path.html#os.path.expanduser)
- dot-delimited Python module path that can be imported in the PyXT virtualenv
  created above

The user script may define multiple `@command` functions and/or import other
modules that define them. Note that other modules must be importable within the
PyXT virtualenv (other techniques such as modifying `sys.path` are also
possible).

## Extension development

### Setup

```sh
python3 -m venv /path/to/virtualenv  # or your preferred way to create a virtualenv
source /path/to/virtualenv/bin/activate
pip install -r requirements.txt -r test-requirements.txt
npm install
```

### Running tests

All tests can be run with *Debug: Select and Start Debugging* command.
Python and JavaScript tests may be run this way once the `.vscode` project
has been loaded.

Python tests may also be run in a terminal

```sh
pytest
```

### Packaging

Build .vsix package

- Update change log
- Update version in `pyxt/__init__.py`
- Update version in `package.json`
- Run `npm install` to update version in lockfile. Verify lockfile changes.

```sh
npm run pkg
```

Install the extension in VS Code

```sh
code --install-extension pyxt-X.Y.Z.vsix
```
