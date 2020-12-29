# PyXT: Python eXTensions for VS Code

A framework for writing Python extensions for VS Code.

## Installation and setup

See [Packaging] below for instructions to build a vsix file.

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

Invoke the _XT: Command Bar_ command to type free-form PyXT commands. Some
commands may be invoked directly from the VS Code  (e.g., _XT: Open File_).

## Commands

- ag - File search with [The Silver Searcher](https://github.com/ggreer/the_silver_searcher).
- history - clear command history.
- open - Open files by path with auto-complete.

### Adding your own custom commands

TODO

## Running tests

All tests can be run with *Debug: Select and Start Debugging* command

Python tests
```sh
nosetests
```

## Packaging

Build vsix package

```sh
npm run pkg
```
