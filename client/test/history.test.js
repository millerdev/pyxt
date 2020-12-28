const assert = require('assert')
const {suite, test} = require('mocha')
const {mockMemento} = require('./util')
const {createHistory} = require("../history")

suite("History storage", () => {
    test("should add item on update", () => {
        const history = createHistory(mockMemento())

        history.update("cmd", "one")

        assert.deepStrictEqual(history.get("cmd"), ["one"])
    })

    test("should not change on update with most recent item", () => {
        const history = createHistory(mockMemento())

        history.update("cmd", "one")
        history.update("cmd", "one")

        assert.deepStrictEqual(history.get("cmd"), ["one"])
    })

    test("should change on update with new item", () => {
        const history = createHistory(mockMemento())

        history.update("cmd", "one")
        history.update("cmd", "two")

        assert.deepStrictEqual(history.get("cmd"), ["two", "one"])
    })

    test("should not save duplicate items", () => {
        const history = createHistory(mockMemento())

        history.update("cmd", "one")
        history.update("cmd", "two")
        history.update("cmd", "one")

        assert.deepStrictEqual(history.get("cmd"), ["one", "two"])
    })

    test("should have a limit of 20 items per command", () => {
        const history = createHistory(mockMemento())

        for (let i = 0; i < 22; i++) {
            history.update("cmd", "arg " + i)
        }

        const items = history.get("cmd")
        assert.strictEqual(items.length, 20)
        assert.strictEqual(items[0], "arg 21")
        assert.strictEqual(items[19], "arg 2")
    })
})
