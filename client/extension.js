"use strict"
const net = require('net')
const path = require('path')
const vscode = require('vscode')
const {workspace} = require('vscode')
const {LanguageClient} = require('vscode-languageclient')
const jsproxy = require("./jsproxy")
const commander = require("./commander")
const {createHistory} = require("./history")
const DEBUG_PORT = 2087
let client

function activate(context) {
    if (isStartedInDebugMode()) {
        client = startLangServerTCP(DEBUG_PORT)
    } else {
        client = startLangServer()
    }
    context.subscriptions.push(client.start())
    jsproxy.publish(client, context)
    commander.subscribe(client, context)
    commander.setHistory(createHistory(context.globalState))
    loadUserScript(client)
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
    const command = workspace.getConfiguration("pyxt").get("pythonPath")
    if (!command) {
        throw new Error("`pyxt.pythonPath` is not set")
    }
    const cwd = path.join(__dirname, "..")
    const args = ["-m", "pyxt"]
    const serverOptions = {command, args, options: {cwd}}
    return new LanguageClient("pyxt", serverOptions, getClientOptions())
}

async function loadUserScript(client) {
    const path = workspace.getConfiguration("pyxt").get("userScript")
    if (!path || !path.trim()) {
        return
    }
    await client.onReady()
    const result = await client.sendRequest(
        "workspace/executeCommand",
        {"command": "load_user_script", "arguments": [path]},
    )
    if (result && result.type === "error") {
        const msg = result.message || "Error loading user script"
        console.error(msg, result)
        vscode.window.showErrorMessage(msg)
    }
}

function getClientOptions() {
    return {outputChannelName: "PyXT Server"}
}

module.exports = {
    activate,
    deactivate
}
