const _ = require("lodash")
const vscode = require('vscode')
const errable = require("./errors").errable

function subscribe(context, client) {
    const clientCommand = async () => await command(client)
    const clientAg = async () => await command(client, "ag ")
    const clientOpen = async () => await command(client, "open ")
    context.subscriptions.push(
        vscode.commands.registerCommand("vsxt.command", clientCommand),
        vscode.commands.registerCommand("vsxt.ag", clientAg),
        vscode.commands.registerCommand("vsxt.openFile", clientOpen)
    )
}

async function command(client, prefix) {
    try {
        const filePath = await commandInput(client, prefix)
        if (filePath) {
            await openFile(filePath)
        }
    } catch (err) {
        vscode.window.showErrorMessage(String(err))
        console.error(err)
    }
}

async function commandInput(client, prefix, completions) {
    const input = vscode.window.createQuickPick()
    try {
        input.placeholder = "XT Command"
        input.ignoreFocusOut = true
        if (completions) {
            setCompletions(input, completions)
        } else {
            getCompletions(input, client, prefix || "")
        }
        input.show()
        if (prefix) {
            input.value = prefix
        }
        const result = await getCommandResult(input, client)
        input.hide()
        if (!result) {
            return
        }
        if (result.type === "items") {
            if (result.filter_results) {
                return filterResults(result, input.value)
            }
            return commandInput(client, result.value, result)
        }
        if (result.type === "success") {
            return result.value
        }
        let message = result.message
        if (!message) {
            message = "Unknown error"
            console.log(message, result)
        }
        throw new Error(message)
    } finally {
        input.dispose()
    }
}

async function getCommandResult(input, client) {
    const disposables = []
    try {
        return await new Promise(resolve => {
            disposables.push(input.onDidChangeValue(errable(value => {
                updateCompletions(input, client, value)
            })))
            disposables.push(input.onDidAccept(errable(() => {
                resolve(doCommand(input, client))
            })))
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
        input.ignoreFocusOut = true
        input.matchOnDescription = true
        input.matchOnDetail = true
        setCompletions(input, result, toQuickPickItem)
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
    console.log(input.items)
}

function updateCompletions(input, client, value) {
    const completions = input._command_completions
    if (completions && input.value.startsWith(completions.value)) {
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
    setCompletions(input, result)
    input.busy = false
}

const debouncedGetCompletions = _.debounce(getCompletions, 200)

function setCompletions(input, completions, transformItem) {
    const items = completions.items.map(transformItem || toAlwaysShown)
    input.items = items
    input._command_completions = {value: input.value, ...completions, items}
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

function doCommand(input, client) {
    const item = input.selectedItems[0]
    let command = input.value || ""
    if (item) {
        if (item.filepath) {
            return {type: "success", value: item.filepath}
        }
        command = command.slice(0, item.offset) + item.label
        if (item.is_completion) {
            input.busy = true
            input.value = command
            return exec(client, "get_completions", command)
        }
    }
    input.busy = true
    return exec(client, "do_command", command)
}

async function exec(client, command, ...args) {
    await client.onReady()
    return client.sendRequest(
        "workspace/executeCommand",
        {"command": command, "arguments": args}
    )
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
    command,
    commandInput,
    splitGoto,
}
