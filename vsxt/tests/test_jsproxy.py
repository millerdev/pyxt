from nose.tools import nottest
from testil import assert_raises, eq

from ..tests.util import async_test
from ..jsproxy import JSProxy


@async_test
async def test_proxy_attrs():
    proxy = test_proxy()
    eq(str(proxy), "JSProxy")
    eq(str(proxy.attr), "JSProxy.attr")
    eq(str(proxy.foo.bar), "JSProxy.foo.bar")
    eq(await proxy.attr, {"name": "attr"})
    eq(await proxy.foo.bar, {"name": "foo", "next": {"name": "bar"}})


@async_test
async def test_proxy_getitem():
    proxy = test_proxy()
    eq(str(proxy[0]), "JSProxy[0]")
    eq(str(proxy.attr[1]), "JSProxy.attr[1]")
    eq(await proxy[0], {"name": 0})
    eq(await proxy.attr[1], {"name": "attr", "next": {"name": 1}})


@async_test
async def test_proxy_call():
    proxy = test_proxy()
    with assert_raises(TypeError, msg="JSProxy is not callable"):
        proxy()
    eq(str(proxy.call()), "JSProxy.call()")
    eq(str(proxy.attr.call(1)), "JSProxy.attr.call(1,)")
    eq(await proxy.call(), {"name": "call", "args": []})
    eq(await proxy.attr.call(1), {
        "name": "attr",
        "next": {"name": "call", "args": [1]}
    })


@async_test
async def test_proxy_call_with_resolved_arg():
    proxy = test_proxy()
    eq(str(proxy.func(proxy.value)), "JSProxy.func(JSProxy.value,)")
    eq(await proxy.func(proxy.value), {"name": "func", "args": [
        {"name": "value", "__resolve__": True}
    ]})


@nottest
def test_proxy():
    server = FakeServer()
    return JSProxy(server)


class FakeServer:

    @property
    def lsp(self):
        return self

    @staticmethod
    async def send_request_async(command, params):
        if command == "vsxt.resolve":
            eq(len(params), 1, params)
            return params[0]
        raise RuntimeError(f"unknown command: {command}")
