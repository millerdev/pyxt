const assert = require('assert')
const {afterEach, beforeEach, suite, test} = require('mocha')
const proxyquire = require('proxyquire')
const util = require("./util")
const commander = proxyquire("../commander", {lodash: util.nodash})

suite('Commander', () => {
    let env, client
    beforeEach(() => {
        client = undefined
        env = util.setup(commander)
    })
    afterEach(() => util.teardown(env, client))

    test("should list commands when first launched", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should load command with args from keybinding", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", filepath: "/file", offset: 5},
            ]}],
        )
        let input
        const args = {text: "open "}
        const result = commander.command(client, "", args)
        input = await env.inputItemsChanged()
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should execute command with args from keybinding", async () => {
        client = util.mockClient(
            // return null value to avoid openFile call, which is hard to test here
            ["do_command", ["open file"], {type: "success", value: null}]
        )
        const args = {text: "open file", exec: true}
        await commander.command(client, "", args)
    })

    test("should execute command returning completions with args from keybinding", async () => {
        client = util.mockClient(
            [
                "do_command", ["open dir/"],
                {type: "items", items: [
                    {label: "file", offset: 5},
                ], value: "open dir/"},
            ]
        )
        let input
        const args = {text: "open dir/", exec: true}
        const result = commander.command(client, "", args)
        input = await env.inputItemsChanged()
        env.assertItems(input, ["file"])
        input.hide()
        assert(!await result)
    })

    test("should show completions on accept command", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            [
                "do_command", ["open"],
                {type: "items", items: [
                    {label: "dir/", offset: 5},
                    {label: "file", offset: 5},
                ], value: "open "},
            ]
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(0, 1)
        input.value = "o"
        env.accept(input)

        input = await env.inputItemsChanged()
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should accept auto-completed command option", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            [
                "do_command", ["open"],
                {type: "items", items: [
                    {label: "dir/", offset: 5},
                    {label: "file", offset: 5},
                ], value: "open "},
            ],
            [
                "do_command", ["open file"],
                {type: "success", value: "file"}
            ],
        )
        let input
        const result = commander.commandInput(client)
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
                {label: "dir/", offset: 5},
                {label: "file", filepath: "/file", offset: 5},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "open ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        assert.strictEqual(await result, "/file")
    })

    test("should accept completion and get more completions", async () => {
        client = util.mockClient(
            ["get_completions", ["ag xyz "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "dir/", is_completion: true, offset: 7},
            ]}],
            ["get_completions", ["ag xyz dir/"], {type: "items", items: [
                {label: "ag xyz dir/", description: "options ...", offset: 0},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "ag xyz ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1, 2)
        env.accept(input)
        input = await env.inputItemsChanged()

        input.hide()
        assert(!await result)
    })

    test("should update value with history item", async () => {
        client = util.mockClient(
            ["get_completions", ["ag "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "ag  .", is_history: true, offset: 0},
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "ag ")
        input = await env.inputItemsChanged()
        await env.activate(1)
        assert.strictEqual(input.value, "ag  .")
        assert(input.pyxt_is_history, "pyxt_is_history should be set")

        await env.activate(2)
        assert.strictEqual(input.value, "ag del ~/mar")
        assert(input.pyxt_is_history, "pyxt_is_history should be set")

        await env.activate(0)
        assert.strictEqual(input.value, "ag ")
        assert(!input.pyxt_is_history, "pyxt_is_history should not be set")

        input.hide()
        assert(!await result)
    })

    test("should not update value with history item starting with typed text", async () => {
        client = util.mockClient(
            ["get_completions", ["ag "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "ag \\bdel ~/mar", is_history: true, offset: 0},
            ]}],
            ["get_completions", ["ag \\"], {type: "items", items: [
                {label: "ag \\bdel ~/mar", is_history: true, offset: 0},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "ag ")
        input = await env.inputItemsChanged()
        input.value = "ag \\"
        input = await env.inputItemsChanged()
        assert.strictEqual(input.value, "ag \\")
        // HACK wait for updateValue -> updateCompletions (should not happen)
        await env.delay(100)
        assert.strictEqual(input.value, "ag \\")

        input.hide()
        assert(!await result)
    })

    test("should reset pyxt_is_history on fetch completions", async () => {
        client = util.mockClient(
            ["get_completions", ["ag "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "ag  .", is_history: true, offset: 0},
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
            ["get_completions", ["ag del ~/ma"], {type: "items", items: [
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "ag ")
        input = await env.inputItemsChanged()
        await env.activate(2)
        assert.strictEqual(input.value, "ag del ~/mar")
        assert(input.pyxt_is_history, "pyxt_is_history should be set")

        await env.changeValue("ag del ~/ma")
        assert(!input.pyxt_is_history, "pyxt_is_history should not be set")

        input.hide()
        assert(!await result)
    })

    test("should change active item", async () => {
        client = util.mockClient(
            ["get_completions", ["ag "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "ag  .", is_history: true, offset: 0},
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
        )
        let input
        const events = []
        const result = commander.commandInput(client, "", "ag ")
        input = await env.inputItemsChanged()
        await env.activate()
        assert.strictEqual(input.value, "ag ")
        env.assertActiveIndex(0)

        /*
        Expected event sequence:

        <Up/Down Arrow key press>
        onDidChangeActive <item>
            updateValue <item>
                setValue <item.label>
        onDidChangeValue <value>
            updateCompletions (ignore due to input.pyxt_ignore_value_changed)
        */
        await env.activate(1)  // simulate arrow key press
        await env.changeValue()
        env.assertActiveIndex(1)
        assert.strictEqual(input.value, "ag  .")

        input.hide()
        assert(!await result)
    })

    test("should not change value on typing -> get completions", async () => {
        client = util.mockClient(
            ["get_completions", ["ag "], {type: "items", items: [
                {label: "", description: "ag xyz ~/project", offset: 0},
                {label: "ag  .", is_history: true, offset: 0},
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
            ["get_completions", ["ag d"], {type: "items", items: [
                {label: "ag del ~/mar", is_history: true, offset: 0},
            ]}],
        )
        let input
        const events = []
        const result = commander.commandInput(client, "", "ag ")
        input = await env.inputItemsChanged()
        await env.activate()  // consume pending onDidChangeActive

        /*
        Expected event sequence:

        <key press (typing in input)>
        onDidChangeValue <typed value>
            updateCompletions <typed value>
        onDidChangeActive undefined (ingored/unexpected)
        onDidChangeActive <new first item>
            updateValue <new first item> (noop: !is_history)
        */
        await env.changeValue("ag d")
        await env.activate()
        env.assertActiveIndex(0)
        assert.equal(input.items[0].label, "")
        assert.strictEqual(input.value, "ag d")

        input.hide()
        assert(!await result)
    })

    test("should do command with command bar value", async () => {
        client = util.mockClient(
            ["get_completions", ["ag x"], {type: "items", items: [
                {label: "ag x", description: "~/project", offset: 0},
            ]}],
            ["do_command", ["ag xyz"], {type: "success", value: ""}]
        )
        let input
        const result = commander.commandInput(client, "", "ag x")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(0, 1)
        input.value = "ag xyz"
        env.accept(input)

        input.hide()
        assert(!await result)
    })

    test("should return file path", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", offset: 5},
            ]}],
            ["do_command", ["open file"], {type: "success", value: "file"}]
        )
        let input
        const result = commander.commandInput(client, "", "open ")
        input = await env.inputItemsChanged()
        input.selectedItems = input.items.slice(1)
        env.accept(input)
        assert.strictEqual(await result, "file")
    })

    test("should error on accept bad command", async () => {
        client = util.mockClient(
            ["get_completions", ["op "], {items: []}],
            ["do_command", ["op "], {type: "error", message: "Unknown command: 'op '"}]
        )
        let input
        const result = commander.commandInput(client, "", "op ")
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
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            ["get_completions", ["ope"], {items: [{label: "open", offset: 0}]}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue("ope")
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should save completed value with completions", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file1", offset: 5},
            ]}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        env.assertItems(input, ["open"])
        assert.strictEqual(input.value, "")

        input._fireDidChangeValue("open ")
        input = await env.inputItemsChanged()
        assert.strictEqual(input.pyxt_completions.value, "open ")
        env.assertItems(input, ["dir/", "file1"])

        input.hide()
        assert(!await result)
    })

    test("should get more completions on complete match", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file1", offset: 5},
            ]}],
            ["get_completions", ["open dir/"], {items: [{label: "file2", offset: 9}]}],
        )
        let input
        const result = commander.commandInput(client, "", "open ")
        input = await env.inputItemsChanged()
        env.assertItems(input, ["dir/", "file1"])

        await env.changeValue("open dir/")
        env.assertItems(input, ["file2"])

        input.hide()
        assert(!await result)
    })

    test("should get completions for first argument", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", offset: 5},
            ]}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue("open ")
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should filter completions", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", offset: 5},
            ]}],
            ["get_completions", ["open d"], {items: [
                {label: "dir/", offset: 5},
            ]}],
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", offset: 5},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "open ")
        input = await env.inputItemsChanged()

        await env.changeValue("open d")
        env.assertItems(input, ["dir/"])
        await env.changeValue("open ")
        env.assertItems(input, ["dir/", "file"])

        input.hide()
        assert(!await result)
    })

    test("should refetch completions on backspace", async () => {
        client = util.mockClient(
            ["get_completions", ["open "], {items: [
                {label: "dir/", offset: 5},
                {label: "file", offset: 5},
            ]}],
            ["get_completions", ["open d"], {items: [{label: "dir/", offset: 5}]}],
            ["get_completions", ["open"], {items: [{label: "open", offset: 0}]}],
        )
        let input
        const result = commander.commandInput(client, "", "open ")
        input = await env.inputItemsChanged()
        await env.changeValue("open d")
        env.assertItems(input, ["dir/"])
        await env.changeValue("open")
        env.assertItems(input, ["open"])

        input.hide()
        assert(!await result)
    })

    test("should show no completions on no match", async () => {
        client = util.mockClient(
            ["get_completions", [""], {items: [{label: "open", offset: 0}]}],
            ["get_completions", ["ox"], {items: []}],
        )
        let input
        const result = commander.commandInput(client)
        input = await env.inputItemsChanged()
        await env.changeValue("ox")
        env.assertItems(input, [])

        input.hide()
        assert(!await result)
    })

    test("should support detail in item completions", async () => {
        client = util.mockClient(
            ["get_completions", ["cmd "], {items: [
                {label: "text 1", detail: "detail 1", offset: 5},
                {label: "text 2", detail: "detail 2", offset: 5},
            ]}],
        )
        let input
        const result = commander.commandInput(client, "", "cmd ")
        input = await env.inputItemsChanged()
        env.assertItems(input, ["text 1/detail 1", "text 2/detail 2"])

        input.hide()
        assert(!await result)
    })

    test("should filter results and return filepath", async () => {
        const items = [
            {label: "1: file 1", detail: "file1", filepath: "/dir/file1", offset: 7},
            {label: "1: file 2", detail: "file2", filepath: "/dir/file2", offset: 7},
        ]
        const results = {type: "items", items, filter_results: true}
        client = util.mockClient(
            ["get_completions", ["ag file"], {items: [], offset: 3}],
            ["do_command", ["ag file"], results],
        )
        let input
        const result = commander.commandInput(client, "", "ag file")
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
            {label: "1: file 1", detail: "file1", filepath: "/dir/file1", offset: 7},
        ]
        client = util.mockClient(
            ["get_completions", ["ag file"], {items: []}],
            ["do_command", ["ag file"], {type: "items", items, filter_results: true}],
        )
        let input
        const result = commander.commandInput(client, "", "ag file")
        input = await env.inputItemsChanged()
        env.accept(input)
        input = await env.inputItemsChanged()

        input.hide()
        assert(!await result)
    })

    test("should show custom placeholder for filter results", async () => {
        client = util.mockClient(
            ["get_completions", ["ag file"], {items: []}],
            ["do_command", ["ag file"], {
                type: "items",
                items: [{label: "result", offset: 0}],
                filter_results: true,
                placeholder: "Custom text"
            }],
        )
        let input
        const result = commander.commandInput(client, "", "ag file")
        input = await env.inputItemsChanged()
        env.accept(input)
        input = await env.inputItemsChanged()
        assert.strictEqual(input.placeholder, "Custom text")

        input.hide()
        assert(!await result)
    })

    suite('with command prefix', () => {
        test("should not add prefix to input value", async () => {
            client = util.mockClient(
                ["get_completions", ["open "], {items: [
                    {label: "dir/", offset: 5},
                    {label: "file", offset: 5},
                ]}],
            )
            let input
            const result = commander.command(client, "open ")
            input = await env.inputItemsChanged()
            assert.strictEqual(input.value, "")
            assert.strictEqual(input.placeholder, "open")

            input.hide()
            assert(!await result)
        })

        test("should do command with prefix", async () => {
            client = util.mockClient(
                ["get_completions", ["ag x"], {type: "items", items: [
                    {label: "ag x", description: "~/project", offset: 0},
                ]}],
                ["do_command", ["ag x"], {type: "success", value: ""}],
            )
            let input
            const result = commander.commandInput(client, "ag ", "x")
            input = await env.inputItemsChanged()
            input.selectedItems = input.items.slice(0, 1)
            env.accept(input)

            input.hide()
            assert(!await result)
        })

        test("should accept completion without prefix", async () => {
            client = util.mockClient(
                ["get_completions", ["ag xyz "], {type: "items", items: [
                    {label: "", description: "ag xyz ~/project", offset: 0},
                    {label: "dir/", is_completion: true, offset: 7},
                ]}],
                ["get_completions", ["ag xyz dir/"], {type: "items", items: [
                    {label: "ag xyz dir/", description: "options ...", offset: 0},
                ]}],
            )
            let input
            const result = commander.commandInput(client, "ag ", "xyz ")
            input = await env.inputItemsChanged()
            input.selectedItems = input.items.slice(1, 2)
            assert.strictEqual(input.value, "xyz ")
            env.accept(input)
            assert.strictEqual(input.value, "xyz dir/")
            input = await env.inputItemsChanged()
            assert.strictEqual(input.value, "xyz dir/")

            input.hide()
            assert(!await result)
        })

        test("should update value with history item", async () => {
            client = util.mockClient(
                ["get_completions", ["ag "], {type: "items", items: [
                    {label: "", description: "ag xyz ~/project", offset: 0},
                    {label: "ag  .", is_history: true, offset: 0},
                    {label: "ag del ~/mar", is_history: true, offset: 0},
                ]}],
            )
            let input
            const result = commander.commandInput(client, "ag ", "")
            input = await env.inputItemsChanged()
            await env.activate(1)
            assert.strictEqual(input.value, " .")
    
            await env.activate(2)
            assert.strictEqual(input.value, "del ~/mar")
    
            await env.activate(0)
            assert.strictEqual(input.value, "")
    
            input.hide()
            assert(!await result)
        })
    
        test("should get completions with prefix", async () => {
            client = util.mockClient(
                ["get_completions", ["open "], {items: [
                    {label: "dir/", offset: 5},
                    {label: "file1", offset: 5},
                ]}],
                ["get_completions", ["open dir/"], {items: [{label: "file2", offset: 9}]}],
            )
            let input
            const result = commander.commandInput(client, "open ", "")
            input = await env.inputItemsChanged()
            env.assertItems(input, ["dir/", "file1"])

            await env.changeValue("dir/")
            env.assertItems(input, ["file2"])

            input.hide()
            assert(!await result)
        })

        test("should filter completions with value from server", async () => {
            client = util.mockClient(
                ["get_completions", ["open dir/"], {value: "open dir/", items: [
                    {label: "dir/", offset: 9},
                    {label: "file", offset: 9},
                ]}],
                ["get_completions", ["open dir/d"], {value: "open dir/d", items: [
                    {label: "dir/", offset: 9},
                ]}],
                ["get_completions", ["open dir/"], {value: "open dir/", items: [
                    {label: "dir/", offset: 9},
                    {label: "file", offset: 9},
                ]}],
            )
            let input
            const result = commander.commandInput(client, "open ", "dir/")
            input = await env.inputItemsChanged()
            assert.strictEqual(input.value, "dir/")
            assert.strictEqual(input.pyxt_completions.value, "open dir/")

            await env.changeValue("dir/d")
            env.assertItems(input, ["dir/"])
            assert.strictEqual(input.value, "dir/d")
            await env.changeValue("dir/")
            env.assertItems(input, ["dir/", "file"])
            assert.strictEqual(input.value, "dir/")

            input.hide()
            assert(!await result)
        })

        test("should prompt on input required", async () => {
            client = util.mockClient(
                ["get_completions", ["ag x"], {type: "items", items: [
                    {label: "ag x", description: "", offset: 0},
                ]}],
                ["do_command", ["ag x"], {
                    type: "items",
                    value: "ag x",
                    items: [
                        {label: "", description: "path is required", offset: 0},
                    ],
                }]
            )
            let input
            const result = commander.commandInput(client, "ag ", "x")
            input = await env.inputItemsChanged()
            assert.strictEqual(input.value, "x")
            input.selectedItems = input.items.slice(0, 1)
            env.accept(input)
            input = await env.inputItemsChanged()
            env.assertItems(input, [""])
            assert.strictEqual(input.value, "x")

            input.hide()
            assert(!await result)
        })

        test("should show full command as results filter placeholder", async () => {
            client = util.mockClient(
                ["get_completions", ["ag file"], {items: []}],
                ["do_command", ["ag file"], {
                    type: "items",
                    items: [{label: "result", offset: 0}],
                    filter_results: true,
                }],
            )
            let input
            const result = commander.commandInput(client, "ag ", "file")
            input = await env.inputItemsChanged()
            assert.strictEqual(input.value, "file")
            env.accept(input)
            input = await env.inputItemsChanged()
            assert.strictEqual(input.placeholder, "ag file")

            input.hide()
            assert(!await result)
        })
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
