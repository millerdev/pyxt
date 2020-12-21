const _ = require("lodash")
const assert = require('assert')
const sinon = require('sinon')
const vscode = require('vscode')

function setup() {
    const sandbox = sinon.createSandbox()
    const inputs = []
    const quickPick = sandbox.stub(vscode.window, "createQuickPick")
    const callbacks = {inputItems: []}
    quickPick.callsFake(() => {
        // keep a reference to each new QuickPick
        const input = quickPick.wrappedMethod.apply(this, arguments)
        inputs.push(input)
        const itemsDescriptor = getPropertyDescriptor(input, "items")
        const items = sandbox.stub(input, "items")
        items.get(itemsDescriptor.get)
        items.set(value => {
            itemsDescriptor.set.call(input, value)
            callbacks.inputItems.forEach(cb => cb(input))
        })
        return input
    })
    const env = {
        accept: input => input._fireDidAccept(),
        changeValue: async (input, value) => {
            const itemsChanged = env.inputItemsChanged()
            input._fireDidChangeValue(value)
            await itemsChanged
        },
        inputItemsChanged: () => new Promise(resolve => {
            function callback(input) {
                _.pull(callbacks.inputItems, callback)
                resolve(input)
            }
            callbacks.inputItems.push(callback)
        }),
        inputSelectionChanged: () => new Promise(resolve => {
            const input = inputs[inputs.length - 1]
            const event = input.onDidChangeSelection(() => {
                event.dispose()
                resolve(input)
            })
        }),

        assertItems: (input, expected) => {
            items = input.items.map(itemText)
            assert.strictEqual(JSON.stringify(items), JSON.stringify(expected))
        },

        sandbox,
    }
    return env
}

function teardown(env, client) {
    client && client.done()
    env.sandbox.restore()
}

function itemText(item) {
    let text = _.isObject(item) ? item.label : JSON.stringify(item)
    if (item.detail) {
        text += "/" + item.detail
    }
    return text
}

/**
 * Mock extension client
 * 
 * Arguments are expected request responses consisting of three-element
 * lists: ["command_name", [args list], {response object}]
 */
function mockClient(...responses) {
    responses = responses.reverse()
    return {
        onReady: async () => undefined,
        sendRequest: async (method, params) => {
            const command = params.command
            const args = params.arguments
            if (!responses.length) {
                assert.fail("unexpected request: " + JSON.stringify(params))
            }
            const response = responses.pop()
            assert.strictEqual(response.length, 3, JSON.stringify(response))
            assert.deepStrictEqual(response.slice(0, 2), [command, args])
            return response[2]
        },
        done: () => {
            const uncalled = responses.reverse().map(JSON.stringify).join("\n")
            assert(!uncalled, "client not called:\n" + uncalled)
        }
    }
}

// Source: https://github.com/sinonjs/sinon/blob/master/lib/sinon/util/core/get-property-descriptor.js
function getPropertyDescriptor(object, property) {
    var proto = object;
    var descriptor;
    var isOwn = Boolean(object && Object.getOwnPropertyDescriptor(object, property));

    while (proto && !(descriptor = Object.getOwnPropertyDescriptor(proto, property))) {
        proto = Object.getPrototypeOf(proto);
    }

    if (descriptor) {
        descriptor.isOwn = isOwn;
    }

    return descriptor;
}

const nodash = {
    debounce: func => func,  // debounce that does not wait
}

module.exports = {
    mockClient,
    nodash,
    setup,
    teardown,
}
