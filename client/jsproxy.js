const _ = require('lodash')
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
