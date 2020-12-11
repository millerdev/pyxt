from nose.tools import nottest
from testil import assert_raises, eq

from ..tests.util import async_test
from ..editor import VSProxy


@async_test
async def test_proxy_attrs():
    proxy = test_proxy()
    eq(str(proxy), "vscode")
    eq(str(proxy.attr), "vscode.attr")
    eq(str(proxy.foo.bar), "vscode.foo.bar")
    eq(await proxy.attr, {"name": "attr"})
    eq(await proxy.foo.bar, {"name": "foo", "next": {"name": "bar"}})


@nottest
def test_proxy():
    server = FakeServer()
    return VSProxy(server)


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
