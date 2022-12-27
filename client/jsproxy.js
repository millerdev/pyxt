const _ = require('lodash')
const vscode = require('vscode')
const errable = require("./errors").errable
const {createHistory} = require("./history")

function withEditor(func) {
    return async function () {
        const editor = vscode.window.activeTextEditor
        if (editor) {
            return await func(editor, ...arguments)
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

function allTextRange(doc) {
    return doc.validateRange(new vscode.Range(0, 0, doc.lineCount, 0))
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

    selections: withEditor((editor, value) => {
        if (!value) {
            return editor.selections.map(sel => pyxtRange(editor, sel))
        } else {
            editor.selections = value.map(sel => selection(editor, sel))
        }
    }),

    get_text: withEditor((editor, range) => {
        const rng = range ? selection(editor, range) : undefined
        return editor.document.getText(rng)
    }),

    get_texts: withEditor((editor, ranges) => {
        return ranges.map(rng => editor.document.getText(selection(editor, rng)))
    }),

    set_text: withEditor((editor, text, range, select=true) => {
        return editor.edit(async builder => {
            const doc = editor.document
            const rng = range ? selection(editor, range) : allTextRange(doc)
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

    set_texts: withEditor((editor, texts, ranges) => {
        const uri = editor.document.uri
        const edits = new vscode.WorkspaceEdit()
        texts.forEach((text, i) => {
            if (ranges[i]) {
                let rng = selection(editor, ranges[i])
                edits.replace(uri, rng, text)
            }
        })
        return vscode.workspace.applyEdit(edits)
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

async function resolve(params) {
    try {
        return await get(namespace[params.root], params)
    } catch (error) {
        console.error(error)
        return ["__error__", error.message, error.stack]
    }
}

async function get(obj, params) {
    let value = obj[params.name]
    if (params.args) {
        if (!value) {
            console.error("not callable", params, value)
            return undefined
        }
        const args = []
        for (var i = 0; i < params.args.length; i++) {
            const arg = params.args[i]
            const shouldResolve = _.isObject(arg) && arg.__resolve__
            args.push(shouldResolve ? await resolve(arg) : arg)
        }
        value = await value.apply(obj, args)
    }
    if (value === undefined) {
        return value
    }
    const next = params.next
    return !next ? value : await get(value, next)
}

module.exports = {
    publish,
}
