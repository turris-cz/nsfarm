import sys
import argparse
from .lxd import __main__ as lxd


def parser(parser):
    subparsers = parser.add_subparsers(help="Utility to be used")
    ret = {None: parser}

    lxd_parser = subparsers.add_parser('lxd', help='Images management')
    lxd_parser.set_defaults(op='lxd')
    ret["lxd"] = lxd.parser(lxd_parser)

    return ret


def handle_args(args, parser_ret):
    handles = {
        "lxd": lxd,
    }
    if hasattr(args, 'op'):
        handles[args.op].handle_args(args, parser_ret[args.op])
    else:
        parser_ret[None].print_usage()
        sys.exit(1)


def main():
    top_parser = argparse.ArgumentParser(description='NSFarm management.')
    parser_ret = parser(top_parser)
    handle_args(top_parser.parse_args(), parser_ret)


if __name__ == '__main__':
    sys.argv[0] = "nsfarm"
    main()
