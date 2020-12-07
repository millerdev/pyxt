function errable(func) {
    // HACK VSCode swallows errors thrown by extensions
    return function () {
        try {
            return func.apply(this, arguments)
        } catch (err) {
            console.error(err)
            throw err
        }
    }
}

module.exports = {
    errable,
}
