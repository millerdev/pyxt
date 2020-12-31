from nose.tools import nottest
from testil import assert_raises, eq

from ..tests.util import async_test
from ..jsproxy import Error, get, JSProxy


@async_test
async def test_proxy_attrs():
    proxy = test_proxy()
    eq(str(proxy), "JSProxy")
    eq(str(proxy.attr), "JSProxy.attr")
    eq(str(proxy.foo.bar), "JSProxy.foo.bar")
    eq(await get(proxy.attr), {"name": "attr", "root": "JSProxy"})
    eq(await get(proxy.foo.bar), {
        "name": "foo",
        "next": {"name": "bar"},
        "root": "JSProxy",
    })


@async_test
async def test_proxy_getitem():
    proxy = test_proxy()
    eq(str(proxy[0]), "JSProxy[0]")
    eq(str(proxy.attr[1]), "JSProxy.attr[1]")
    eq(await get(proxy[0]), {"name": 0, "root": "JSProxy"})
    eq(await get(proxy.attr[1]), {
        "name": "attr",
        "next": {"name": 1},
        "root": "JSProxy",
    })


@async_test
async def test_proxy_call():
    proxy = test_proxy()
    with assert_raises(TypeError, msg="JSProxy is not callable"):
        proxy()
    eq(str(proxy.call()), "JSProxy.call()")
    eq(str(proxy.attr.call(1)), "JSProxy.attr.call(1,)")
    eq(await get(proxy.call()), {"name": "call", "args": [], "root": "JSProxy"})
    eq(await get(proxy.attr.call(1)), {
        "name": "attr",
        "next": {"name": "call", "args": [1]},
        "root": "JSProxy",
    })


@async_test
async def test_proxy_call_with_resolved_arg():
    proxy = test_proxy()
    eq(str(proxy.func(proxy.value)), "JSProxy.func(JSProxy.value,)")
    eq(await get(proxy.func(proxy.value)), {"name": "func", "args": [
        {"name": "value", "__resolve__": True, "root": "JSProxy"}
    ], "root": "JSProxy"})


@async_test
async def test_proxy_error():
    proxy = test_proxy(ErrorServer())
    with assert_raises(Error, msg="something is wrong"):
        await get(proxy.attr)


@nottest
def test_proxy(server=None):
    server = server or FakeServer()
    return JSProxy(server, root="JSProxy")


class FakeServer:

    @property
    def lsp(self):
        return self

    @staticmethod
    async def send_request_async(command, params):
        if command == "pyxt.resolve":
            eq(len(params), 1, params)
            return params[0]
        raise RuntimeError(f"unknown command: {command}")


class ErrorServer(FakeServer):

    @staticmethod
    async def send_request_async(command, params):
        return ["__error__", "something is wrong", "stack trace"]
