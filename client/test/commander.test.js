const assert = require('assert')
const {afterEach, beforeEach, suite, test} = require('mocha')
const util = require("./util")
const commander = require("../commander")

suite('Commander', () => {
    let env, client
    beforeEach(() => {
        client = undefined
        env = util.setup()
    })
    afterEach(() => util.teardown(env, client))

    test("should list commands when first launched", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should show completions on accept command", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
            [
                "do_command", ["open"],
                {type: "items", items: ["dir/", "file"], offset: 5, value: "open "}
            ]
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(0, 1)
        env.accept(input)

        input = await env.inputItemsChanged()
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should accept auto-completed command option", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
            [
                "do_command", ["open"],
                {type: "items", items: ["dir/", "file"], value: "open ", offset: 5}
            ],
            [
                "do_command", ["open file"],
                {type: "success", value: "file"}
            ],
        )
        let input
        const result = commander.commandInput(client, "")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(0, 1)
        env.accept(input)
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        assert.strictEqual(await result, "file")
    })

    test("should return file path", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: ["dir/", "file"], offset: 5}],
            ["do_command", ["open file"], {type: "success", value: "file"}]
        )
        let input
        const result = commander.commandInput(client, "open ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1)
        env.accept(input)
        assert.strictEqual(await result, "file")
    })

    test("should error on accept bad command", async () => {
        client = util.mockClient(
            ["get_completions", ["op "], {items: [], offset: 0}],
            ["do_command", ["op "], {type: "error", message: "Unknown command: 'op '"}]
        )
        let input
        const result = commander.commandInput(client, "op ")
        input = await env.inputItemsChanged()
        env.assertItems(input, [])
        env.accept(input)
        try {
            await result
            assert.fail("error not thrown")
        } catch (err) {
            assert.strictEqual(err.message, "Unknown command: 'op '")
        }
    })

    test("should not get more completions on match existing item", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue(input, "ope")
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should get completions for first argument", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
            ["get_completions", ["open "], {items: ["dir/", "file"], offset: 5}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue(input, "open ")
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should filter completions", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: ["dir/", "file"], offset: 5}],
        )
        let input
        const result = commander.commandInput(client, "open ")
        input = await env.inputItemsChanged()

        await env.changeValue(input, "open d")
        env.assertItems(input, ["dir/"])
        await env.changeValue(input, "open ")
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should refetch completions on backspace", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: ["dir/", "file"], offset: 5}],
            ["get_completions", ["open"], {items: ["open"], offset: 0}],
        )
        let input
        const result = commander.commandInput(client, "open ")
        input = await env.inputItemsChanged()
        await env.changeValue(input, "open d")
        env.assertItems(input, ["dir/"])
        await env.changeValue(input, "open")
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should show no completions on no match", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: ["open"], offset: 0}],
            ["get_completions", ["ox"], {items: [], offset: 0}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue(input, "ox")
        env.assertItems(input, [])

        input.hide()
        assert(!await result)
    })
})
