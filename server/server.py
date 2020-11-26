from pygls.server import LanguageServer


class XTServer(LanguageServer):
    CMD_XT_COMMAND = "xtCommand"


xt_server = XTServer()


@xt_server.command(XTServer.CMD_XT_COMMAND)
def xt_command(server: XTServer, *args):
    server.show_message("XT!")
