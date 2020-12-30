# PyXT: Python eXTensions for VS Code

A framework for writing Python extensions for VS Code.

## Installation and setup

See [Packaging](#packaging) below for instructions to build the .vsix file.

- Setup a virtualenv with Python 3.7+
  ```sh
  python3 -m venv /path/to/your/virtualenv
  ```
- Install requirements in the virtualenv (you may prefer to use the tag of the
  version being installed rather than `master`)
  ```sh
  /path/to/your/virtualenv/bin/pip install -r \
    https://github.com/millerdev/PyXT/raw/master/requirements.txt
  ```
- Install the extension in VS Code
  ```sh
  code --install-extension ./pyxt-X.Y.Z.vsix
  ```
- Reload VS Code
- Open Settings in VS Code and search for `pyxt.pythonPath`. Set the value to
  the path of the `python` executable in the virtualenv created above. Something
  like `/path/to/your/virtualenv/bin/python`.
- Reload VS Code again? (not sure if this is necessary)

## Usage

Type Ctrl+Shift+P and select _XT: Command_ to open the PyXT command bar.

Some commands may also be invoked directly as VS Code commands (e.g.,
_XT: Open File_), and may be assigned a keyboard shortcut.

## Commands

- `ag MATCH PATH OPTIONS...` - [The Silver Searcher](https://github.com/ggreer/the_silver_searcher) code
  search. Ag must be installed separately.  
  VS Code command: _XT: Ag (The Silver Searcher)_.
- `history COMMAND` - clear command history. Confirmation is required before history is
  deleted.
- `open FILE_PATH` - Open files by path with auto-complete. The entered path is relative to
  the location of the active text editor's file by default. It may also start
  with `~` (home directory prefix). Absolute paths are supported as well.  
  VS Code command: _XT: Open File_.

The command name should not be typed when it is invoked directly via its
VS Code command (rather than with the PyXT command bar). In this case, simply
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

### Adding your own custom commands

TODO

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
nosetests
```

### Packaging

Build .vsix package

```sh
npm run pkg
```
