from nose.tools import nottest
from testil import eq

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
