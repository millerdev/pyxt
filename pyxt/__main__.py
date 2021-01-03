import argparse
import logging

from .server import pyxt_server


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.tcp else logging.WARNING)
    if args.tcp:
        pyxt_server.start_tcp(args.host, args.port)
    else:
        pyxt_server.start_io()


def add_arguments(parser):
    parser.description = "PyXT Server"
    parser.add_argument(
        "--tcp", action="store_true",
        help="Use TCP server (debug mode)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Bind to this address"
    )
    parser.add_argument(
        "--port", type=int, default=2087,
        help="Bind to this port"
    )


if __name__ == '__main__':
    main()
