0.3.6 - 2022-01-04

- No user-facing changes.
- (internal) Add `UnlimitedString` parser argument type

0.3.5 - 2021-06-18

- Fix `replace ... all` fails with error.
- Fix edit history command.
- Fix type new command matching first characters of history item.
- Fix tests in VS Code 1.57.0

0.3.4 - 2021-05-31

- Add `replace` command.
- Allow command from history to be edited before execution.


0.3.3 - 2021-02-13

- Fix `ag` command handling of very long line matches.


0.3.2 - 2021-02-05

- Fix isort entire document (not selection).
- Improve error handling on get command completions.
- Execute all selections with "python" command.


0.3.0 - 2021-01-22

- Add "history redo COMMAND" to redo most recent invocation of command.
- Change "history COMMAND" to "history clear COMMAND". History is cleared
  immediately on command execution.
- Move most history logic into Python.
- Use webpack for JS packaging => much smaller vsix file.


0.2.0 - 2021-01-15

- Add support for custom keybindings.
- Limit `ag` result item length to 150.
- Limit `ag` result count to maximum of 200.
- Show current directory in open file placeholder
- Log errors to PyXT output channel in VS Code.


0.1.0 - 2021-01-03

- Initial release.
