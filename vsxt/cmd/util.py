from ..command import get_context
from ..results import result


def input_required(message, args):
    cmdstr = get_context(args).input_value
    return result([{"label": "", "description": message}], cmdstr)
