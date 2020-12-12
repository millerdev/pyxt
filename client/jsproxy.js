const vscode = require('vscode')
const errable = require("./errors").errable

function publish(client) {
    client.onReady().then(errable(() => {
        client.onRequest("vsxt.resolve", errable(resolve))
    }))
}

function resolve(params) {
    return get(vscode, params)
}

function get(obj, params) {
    const value = obj[params.name]
    const next = params.next
    return !next ? value : get(value, next)
}

module.exports = {
    publish,
}
