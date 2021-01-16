const _ = require('lodash')
const vscode = require('vscode')
const errable = require("./errors").errable
const {createHistory} = require("./history")

function withEditor(func) {
    return function () {
        const editor = vscode.window.activeTextEditor
        if (editor) {
            return func(editor, ...arguments)
        }
    }
}

/**
 * Convert VS Code selection (two positions) to PyXT range (two offsets)
 *
 * The first element of a PyXT range is the selection "anchor" and the
 * second is the "active" or end with the cursor.
 */
function pyxtRange(editor, selection) {
    const doc = editor.document
    return [doc.offsetAt(selection.anchor), doc.offsetAt(selection.active)]
}

/**
 * Convert PyXT range to selection
 */
function selection(editor, pyxtrange) {
    const doc = editor.document
    const [anchor, active] = pyxtrange
    return new vscode.Selection(doc.positionAt(anchor), doc.positionAt(active))
}

/**
 * Interface for text manipulation on the active text editor
 */
const editor = {
    selection: withEditor((editor, value) => {
        if (!value) {
            return pyxtRange(editor, editor.selection)
        } else {
            editor.selection = selection(editor, value)
        }
    }),

    get_text: withEditor((editor, range) => {
        const rng = range ? selection(editor, range) : undefined
        return editor.document.getText(rng)
    }),

    set_text: withEditor((editor, text, range, select=true) => {
        editor.edit(async builder => {
            const doc = editor.document
            const rng = range ? selection(editor, range) : undefined
            await builder.replace(rng, text)
            let start = rng ? rng.start : doc.positionAt(0)
            let end = doc.positionAt(doc.offsetAt(start) + text.length)
            if (range && range[0] > range[1]) {
                [start, end] = [end, start]
            }
            if (!select) {
                start = end
            }
            editor.selection = new vscode.Selection(start, end)
        })
    }),
}

const namespace = {
    "vscode": vscode,
    "editor": editor,
    "history": null,
}

function publish(client, context) {
    namespace.history = createHistory(context.globalState)
    client.onReady().then(errable(() => {
        client.onRequest("pyxt.resolve", resolve)
    }))
}

function resolve(params) {
    try {
        return get(namespace[params.root], params)
    } catch (error) {
        console.error(error)
        return ["__error__", error.message, error.stack]
    }
}

function get(obj, params) {
    let value = obj[params.name]
    if (params.args) {
        if (!value) {
            console.error("not callable", params, value)
            return undefined
        }
        const args = _.map(params.args, arg =>
            _.isObject(arg) && arg.__resolve__ ? resolve(arg) : arg
        )
        value = value.apply(obj, args)
    }
    if (value === undefined) {
        return value
    }
    const next = params.next
    return !next ? value : get(value, next)
}

module.exports = {
    publish,
}
