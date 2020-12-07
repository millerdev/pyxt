const _ = require("lodash")
const vscode = require('vscode')
const errable = require("./errors").errable

function publish(client) {
    client.onReady().then(errable(() => {
        client.onRequest("vsxt.getProp", errable(getProp))
    }))
}

function getProp(path) {
    return _.get(vscode, path)
}

module.exports = {
    publish,
}
