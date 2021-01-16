const HISTORY = "history"

function createHistory(state) {
    return {

        /**
         * Get history array for cmd, most recent first
         */
        get: cmd => (state.get(keyOf(cmd)) || []),

        /**
         * Add value to cmd history
         *
         * Move value to the most recent command if it is already in the
         * history for cmd.
         */
        update: (cmd, value) => {
            const key = keyOf(cmd)
            let items = state.get(key) || []
            if (items.length) {
                if (items[0] === value) {
                    return  // same as most recent command (no change)
                }
                items = items.filter(item => item !== value).slice(0, 9)
            }
            items.unshift(value)
            state.update(key, items)
        },

        /**
         * Clear command history
         */
        clear: cmd => state.update(keyOf(cmd), [])
    }
}

function keyOf(cmd) {
    return HISTORY + "." + cmd.trim()
}

module.exports = {createHistory}
