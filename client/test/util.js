const _ = require("lodash")
const assert = require('assert')
const sinon = require('sinon')
const vscode = require('vscode')

function setup(commander) {
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
        get input() { return inputs.length ? inputs[inputs.length - 1] : null},
        accept: input => input._fireDidAccept(),
        activate: (index) => new Promise(resolve => {
            console.log(`  activate(${index || ''})`)
            const input = env.input
            const event = input.onDidChangeActive(() => {
                event.dispose()
                if (input.pyxt_value_timeout) {
                    // HACK trigger timeout to force update value
                    input.pyxt_value_timeout._onTimeout()
                    clearTimeout(input.pyxt_value_timeout)
                    delete input.pyxt_value_timeout
                }
                setTimeout(() => resolve(input))
            })
            if (index !== undefined) {
                input.activeItems = [input.items[index]]
            }
        }),
        changeValue: async (value) => {
            // Change value as if typing (value !== undefined)
            // or return promise for next onDidChangeValue event
            if (value !== undefined) {
                console.log(`  changeValue(${JSON.stringify(value)})`)
                const itemsChanged = env.inputItemsChanged()
                env.input.value = value
                await itemsChanged
            } else {
                console.log(`  changeValue()`)
                return env._valueChanged()
            }
        },
        _valueChanged: () => new Promise(resolve => {
            const input = env.input
            const event = input.onDidChangeValue(() => {
                event.dispose()
                setTimeout(() => resolve(input.value))
            })
        }),
        inputItemsChanged: () => new Promise(resolve => {
            function callback(input) {
                _.pull(callbacks.inputItems, callback)
                setTimeout(() => resolve(input))
            }
            callbacks.inputItems.push(callback)
        }),
        inputSelectionChanged: () => new Promise(resolve => {
            const input = env.input
            const event = input.onDidChangeSelection(() => {
                event.dispose()
                resolve(input)
            })
        }),
        delay: ms => new Promise(resolve => setTimeout(resolve, ms)),

        assertItems: (input, expected) => {
            items = input.items.map(itemText)
            assert.strictEqual(JSON.stringify(items), JSON.stringify(expected))
        },
        assertActiveIndex: (index) => {
            const input = env.input
            const [item] = input.activeItems
            assert.strictEqual(input.items.indexOf(item), index, `active item: ${item}`)
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
    const unexpected = []
    return {
        onReady: async () => undefined,
        sendRequest: async (method, params) => {
            const command = params.command
            const args = params.arguments
            if (!responses.length) {
                const msg = "unexpected request: " + JSON.stringify(params)
                unexpected.push(msg)
                assert.fail(msg)
            }
            const response = responses.pop()
            assert.strictEqual(response.length, 3, JSON.stringify(response))
            assert.deepStrictEqual(response.slice(0, 2), [command, args])
            return response[2]
        },
        done: () => {
            const errors = []
            if (unexpected.length) {
                errors.push("Unexpected requests:")
                errors.push(...unexpected)
            }
            if (responses.length) {
                errors.push("Pending requests")
                errors.push(responses.reverse().map(JSON.stringify).join("\n"))
            }
            assert(!errors.length, errors.join("\n"))    
        }
    }
}

function mockMemento() {
    const state = {}
    return {
        get: key => (state[key] || []),
        update: (key, value) => {
            state[key] = value
        },
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
    mockMemento,
    nodash,
    setup,
    teardown,
}
