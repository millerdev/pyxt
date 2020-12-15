# VSXT: VS Code extensions in Python

A collection of VS Code commands implemented in Python.

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

Install

```sh
code --install-extension ./vsxt-X.Y.Z.vsix
```
