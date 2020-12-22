const assert = require('assert')
const {afterEach, beforeEach, suite, test} = require('mocha')
const proxyquire = require('proxyquire')
const util = require("./util")
const commander = proxyquire("../commander", {lodash: util.nodash})

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

    test("should accept completion with filepath", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                "dir/",
                {label: "file", filepath: "/file"},
            ], offset: 5}],
        )
        let input
        const result = commander.commandInput(client, "open ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        assert.strictEqual(await result, "/file")
    })

    test("should accept completion and get more completions", async () => {
        client = util.mockClient(
            ["get_completions", ["ag xyz "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project"},
                {label: "dir/", is_completion: true},
            ], offset: 7}],
            ["get_completions", ["ag xyz dir/"], {type: "items", items: [
                {label: "", description: "ag xyz dir/"},
            ], offset: 11}],
        )
        let input
        const result = commander.commandInput(client, "ag xyz ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        input = await env.inputItemsChanged()

        input.hide()
        assert(!await result)
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

    test("should get more completions on complete match", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: ["dir/", "file1"], offset: 5}],
            ["get_completions", ["open dir/"], {items: ["file2"], offset: 9}],
        )
        let input
        const result = commander.commandInput(client, "open ")
        input = await env.inputItemsChanged()
        env.assertItems(input, ["dir/", "file1"])

        await env.changeValue(input, "open dir/")
        input = await env.inputItemsChanged()
        env.assertItems(input, ["file2"])

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

    test("should support detail in item completions", async () => {
        client = util.mockClient(
            ["get_completions", ["cmd "], {items: [
                {label: "text 1", detail: "detail 1"},
                {label: "text 2", detail: "detail 2"},
            ], offset: 5}],
        )
        let input
        const result = commander.commandInput(client, "cmd ")
        input = await env.inputItemsChanged()
        env.assertItems(input, ["text 1/detail 1", "text 2/detail 2"])

        input.hide()
        assert(!await result)
    })

    test("should filter results and return filepath", async () => {
        const items = [
            {label: "1: file 1", detail: "file1", filepath: "/dir/file1"},
            {label: "1: file 2", detail: "file2", filepath: "/dir/file2"},
        ]
        const results = {type: "items", items, offset: 7, filter_results: true}
        client = util.mockClient(
            ["get_completions", ["ag file"], {items: [], offset: 3}],
            ["do_command", ["ag file"], results],
        )
        let input
        const result = commander.commandInput(client, "ag file")
        input = await env.inputItemsChanged()
        env.accept(input)
        input = await env.inputItemsChanged()
        assert.strictEqual(input.value, "")
        assert.deepStrictEqual(input.items, items)
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        assert.strictEqual(await result, "/dir/file2")
    })

    test("should not return filepath on cancel filtered results", async () => {
        const items = [
            {label: "1: file 1", detail: "file1", filepath: "/dir/file1"},
        ]
        const results = {type: "items", items, offset: 7, filter_results: true}
        client = util.mockClient(
            ["get_completions", ["ag file"], {items: [], offset: 3}],
            ["do_command", ["ag file"], results],
        )
        let input
        const result = commander.commandInput(client, "ag file")
        input = await env.inputItemsChanged()
        env.accept(input)
        input = await env.inputItemsChanged()

        input.hide()
        assert(!await result)
    })
})


suite('Commander splitGoto utility', () => {
    test("should handle path without goto", () => {
        const path = "file:///path/to/file.ext"
        const result = commander.splitGoto(path)
        assert.deepStrictEqual(result, [path, null])
    })

    test("should handle path with goto line", () => {
        const path = "file:///path/to/file.ext"
        const result = commander.splitGoto(path + ":14")
        assert.deepStrictEqual(result, [path, {line: 14, start: 0, length: 0}])
    })

    test("should handle path with goto line and position", () => {
        const path = "file:///path/to/file.ext"
        const result = commander.splitGoto(path + ":14:9")
        assert.deepStrictEqual(result, [path, {line: 14, start: 9, length: 0}])
    })

    test("should handle path with goto line and selection", () => {
        const path = "file:///path/to/file.ext"
        const result = commander.splitGoto(path + ":14:9:3")
        assert.deepStrictEqual(result, [path, {line: 14, start: 9, length: 3}])
    })
})
