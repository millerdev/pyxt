"use strict"
const net = require('net')
const path = require('path')
const workspace = require('vscode').workspace
const LanguageClient = require('vscode-languageclient').LanguageClient
const api = require("./api")
const commander = require("./commander")
const DEBUG_PORT = 2087
let client

function activate(context) {
    if (isStartedInDebugMode()) {
        client = startLangServerTCP(DEBUG_PORT)
    } else {
        client = startLangServer()
    }
    context.subscriptions.push(client.start())
    api.publish(client)
    commander.subscribe(context, client)
}

function deactivate() {
    return client ? client.stop() : Promise.resolve()
}

function isStartedInDebugMode() {
    return process.env.VSCODE_DEBUG_MODE === "true"
}

function startLangServerTCP(addr) {
    const serverOptions = () => {
        return new Promise((resolve, reject) => {
            const clientSocket = new net.Socket()
            clientSocket.connect(addr, "127.0.0.1", () => {
                resolve({reader: clientSocket, writer: clientSocket})
            })
        })
    }
    return new LanguageClient(`tcp lang server (port ${addr})`, serverOptions, getClientOptions())
}

function startLangServer() {
    const pythonPath = workspace.getConfiguration("python").get("pythonPath")
    if (!pythonPath) {
        throw new Error("`python.pythonPath` is not set")
    }
    const cwd = path.join(__dirname, "..", "..")
    const args = ["-m", "vsxt"]
    const serverOptions = {args, pythonPath, options: { cwd }}
    return new LanguageClient(pythonPath, serverOptions, getClientOptions())
}

function getClientOptions() {
    return {outputChannelName: "XT Server"}
}

module.exports = {
    activate,
    deactivate
}
