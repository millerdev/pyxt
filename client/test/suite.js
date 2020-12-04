glob = require("glob")
Mocha = require("mocha")
path = require("path")

function run() {
    const mocha = new Mocha({ui: 'tdd', color: true})
    const testsRoot = __dirname

    return new Promise((ok, error) => {
        glob('**/**.test.js', { cwd: testsRoot }, (err, files) => {
            if (err) {
                return error(err)
            }

            files.forEach(f => mocha.addFile(path.resolve(testsRoot, f)))

            try {
                mocha.run(failures => {
                    if (failures > 0) {
                        error(new Error(`${failures} tests failed.`))
                    } else {
                        ok()
                    }
                })
            } catch (err) {
                error(err)
            }
        })
    })
}

module.exports = {run}
