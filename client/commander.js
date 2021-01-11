const _ = require("lodash")
const vscode = require('vscode')
const jsonrpc = require('vscode-jsonrpc')
const errable = require("./errors").errable
const pkg = require("../package.json")
let history

function subscribe(getClient, context) {
    pkg.contributes.commands.forEach(cmd => {
        registerCommand(cmd.command, getClient, context)
    })
}

function registerCommand(id, getClient, context) {
    const slug = id === "pyxt.command" ? "" : (id.slice(5) + " ")
    const reg = vscode.commands.registerCommand(id, args => {
        const client = getClient()
        client && command(client, slug, args)
    })
    context.subscriptions.push(reg)
}

function setHistory(value) {
    history = value
}

async function command(client, cmd="", args={}) {
    const value = args.text || ""
    let filePath
    try {
        if (args.exec) {
            const result = await exec(client, "do_command", cmd + value)
            filePath = await dispatch(result, client, cmd, value)
        } else {
            filePath = await commandInput(client, cmd, value)
        }
        if (filePath) {
            await openFile(filePath)
        }
    } catch (err) {
        vscode.window.showErrorMessage(String(err))
        console.error(err)
    }
}

async function commandInput(client, cmd="", value="", completions) {
    const input = vscode.window.createQuickPick()
    try {
        input.placeholder = cmd.trim() || "PyXT Command"
        input.sortByLabel = false
        input.ignoreFocusOut = true
        input.pyxt_cmd = cmd
        if (completions) {
            setCompletions(input, cmd + value, completions)
        } else {
            getCompletions(input, client, cmd + value)
        }
        input.show()
        input.value = value
        const result = await getCommandResult(input, client)
        input.hide()
        return dispatch(result, client, cmd, input.value)
    } finally {
        input.dispose()
    }
}

function dispatch(result, client, cmd, value) {
    if (!result) {
        return Promise.resolve()
    }
    if (result.type === "items") {
        if (result.filter_results) {
            return filterResults(result, cmd + value)
        }
        if (result.clear_history && result.command) {
            return clearHistory(result)
        }
        if (result.value) {
            value = result.value.slice(cmd.length)
        }
        return commandInput(client, cmd, value, result)
    }
    if (result.type === "success") {
        return Promise.resolve(result.value)
    }
    let message = result.message
    if (!message) {
        message = "Unknown error"
        console.log(message, result)
    }
    throw new Error(message)
}

async function getCommandResult(input, client) {
    const disposables = []
    try {
        return await new Promise(resolve => {
            disposables.push(input.onDidChangeValue(errable(value => {
                updateCompletions(input, client, value)
            })))
            disposables.push(input.onDidAccept(async () => {
                try {
                    const promise = doCommand(input, client)
                    disposables.push(promise)
                    resolve(await promise)
                    disposables.pop()
                } catch (err) {
                    console.error(err)
                    throw err
                }
            }))
            disposables.push(input.onDidHide(errable(() => resolve())))
        })
    } finally {
        disposables.forEach(d => d.dispose())
    }
}

async function filterResults(result, command) {
    const input = vscode.window.createQuickPick()
    const disposables = [input]
    try {
        input.placeholder = result.placeholder || command
        input.sortByLabel = false
        input.ignoreFocusOut = true
        input.matchOnDescription = true
        input.matchOnDetail = true
        setCompletions(input, command, result, toQuickPickItem, true)
        input.show()
        const item = await new Promise(resolve => {
            if (!result.keep_empty_details) {
                const change = input.onDidChangeValue(errable(value => {
                    distributeDetails(input)
                    change.dispose()
                }))
                disposables.push(change)
            }
            disposables.push(input.onDidAccept(errable(() => {
                resolve(input.selectedItems[0])
            })))
            disposables.push(input.onDidHide(errable(() => resolve())))
        })
        if (item && item.copy) {
            input.busy = true
            await vscode.env.clipboard.writeText(item.label)
        }
        input.hide()
        return item && item.filepath
    } finally {
        disposables.forEach(d => d.dispose())
    }
}

/**
 * Copy "detail" to items without starting with the last item
 * 
 * This is useful when items are results from files where only the final
 * result from each file is tagged with a detail. Upon filtering it is
 * useful to have that context on every item.
 */
function distributeDetails(input) {
    let detail = undefined
    Array.from(input.items).reverse().forEach(item => {
        if (item.detail) {
            detail = item.detail
        } else {
            item.detail = detail
        }
    })
    input.items = input.items
}

function updateCompletions(input, client, value) {
    const completions = input.pyxt_completions
    value = input.pyxt_cmd + value
    if (completions && value.startsWith(completions.value)) {
        const matching = completions.items.filter(item => {
            const term = value.slice(item.offset)
            return item.label.startsWith(term)
        })
        if (matching.length) {
            input.items = matching
            if (matching.length > 1 || matching.some(item =>
                item.label.length > value.slice(item.offset).length
            )) {
                return
            }
        }
    }
    debouncedGetCompletions(input, client, value);
}

async function getCompletions(input, client, value) {
    input.busy = true
    const result = await exec(client, "get_completions", value)
    setCompletions(input, value, result)
    input.busy = false
}

const debouncedGetCompletions = _.debounce(getCompletions, 200)

function setCompletions(input, value, completions, transformItem, noHistory) {
    if (completions.placeholder) {
        input.placeholder = completions.placeholder
    }
    const items = completions.items.map(transformItem || toAlwaysShown)
    input.items = noHistory ? items : addHistory(items, value)
    input.pyxt_completions = {value, ...completions, items}
}

function toAlwaysShown(item) {
    item = toQuickPickItem(item)
    item.alwaysShow = true
    return item
}

function toQuickPickItem(item) {
    if (_.isString(item)) {
        item = {label: item}
    } else if (!_.isObject(item)) {
        item = {label: String(item)}
    }
    return item
}

async function doCommand(input, client) {
    const item = input.selectedItems[0]
    let command = input.pyxt_cmd + input.value
    if (item) {
        if (item.filepath) {
            // TODO save history
            return disposable({type: "success", value: item.filepath})
        }
        if (item.is_completion || item.offset > 0 || item.label.startsWith(command)) {
            command = command.slice(0, item.offset) + item.label
            if (item.is_completion) {
                input.busy = true
                input.value = command.slice(input.pyxt_cmd.length)
                return exec(client, "get_completions", command)
            }
        }
    }
    input.busy = true
    const result = await exec(client, "do_command", command)
    updateHistory(command, result)
    return result
}

function disposable(value) {
    promise = Promise.resolve(value)
    promise.dispose = () => null
    return promise
}

function exec(client, command, ...args) {
    const can = new jsonrpc.CancellationTokenSource()
    const promise = (async () => {
        await client.onReady()
        return client.sendRequest(
            "workspace/executeCommand",
            {"command": command, "arguments": args},
            can.token
        )
    })()
    promise.dispose = () => can.cancel()
    return promise
}

function updateHistory(command, result) {
    const [cmd, value] = splitCommand(command)
    if (result && value && !result.no_history) {
        if (result.type === "success") {
            history.update(cmd, value)
        } else if (result.type === "items" && result.filter_results) {
            history.update(cmd, value)
        }
    }
}

function addHistory(items, command) {
    const [cmd, value] = splitCommand(command)
    const hist = history.get(cmd)
        .filter(item => item.startsWith(value))
        .map(label => cmd + " " + label)
        .map(label => ({label, offset: 0}))
    if (hist.length) {
        const zero = items.length ? items[0] : null
        if (zero && zero.offset === 0) {
            items = [zero].concat(hist).concat(items.slice(1))
        } else {
            items = hist.concat(items)
        }
    }
    return items
}

async function clearHistory(result) {
    const answer = await vscode.window.showInputBox({
        placeHolder: `Type "CLEAR" to delete '${result.command}' command history`,
    })
    if (answer === "CLEAR") {
        history.clear(result.command)
        vscode.window.showInformationMessage(
            `'${result.command}' command history has been deleted.`
        )
    } else if (answer !== undefined) {
        vscode.window.showWarningMessage("Bad input: " + answer)
    }
}

function splitCommand(command) {
    return command.split(/ (.*)/, 2)
}

async function openFile(path) {
    let goto
    [path, goto] = splitGoto(path)
    const document = await vscode.workspace.openTextDocument(path);
    if (!document) {
        throw new Error("Not found: " + path);
    }
    const editor = await vscode.window.showTextDocument(document);
    if (!editor) {
        throw new Error("Cannot open " + path);
    }
    if (goto) {
        const rng = new vscode.Selection(
            new vscode.Position(goto.line, goto.start),
            new vscode.Position(goto.line, goto.start + goto.length)
        )
        editor.selection = rng
        editor.revealRange(rng)
    }
}

function splitGoto(path) {
    const re = /(?<path>.*?)(?::(?<line>\d+)(?::(?<start>\d+)(?::(?<length>\d+))?)?)?$/
    const match = re.exec(path)
    return [match.groups.path, match.groups.line ? {
        line: parseInt(match.groups.line),
        start: parseInt(match.groups.start || 0),
        length: parseInt(match.groups.length || 0),
    } : null]
}

module.exports = {
    subscribe,
    setHistory,
    command,
    commandInput,
    splitGoto,
}
