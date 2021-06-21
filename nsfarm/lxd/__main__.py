import sys
import argparse
import subprocess
import dateutil.relativedelta
from . import utils
from . import Container, LXDConnection


def parser(parser):
    subparsers = parser.add_subparsers()

    clean = subparsers.add_parser('clean', help='Remove old and unused containers')
    clean.set_defaults(lxd_op='clean')
    clean.add_argument(
        'DELTA',
        nargs='?',
        default=dateutil.relativedelta.relativedelta(weeks=1),
        type=parse_deltatime,
        help="""Time delta for how long image should not be used to be cleaned (removed). In default if not specified
        '1w' is used. Format is expect to be a number with suffix. Supported suffixes are m(inute), h(our), d(ay) and
        w(eek).
        """
    )
    clean.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help='Print what would be removed but do nothing.'
    )

    bootstrap = subparsers.add_parser('bootstrap', help='Bootstrap specific or all images')
    bootstrap.set_defaults(lxd_op='bootstrap')
    bootstrap.add_argument(
        'IMG',
        nargs='*',
        help='Name of image to bootstrap.'
    )
    bootstrap.add_argument(
        '-a', '--all',
        action='store_true',
        help='Bootstrap all images present instead of only listed ones.'
    )

    inspect = subparsers.add_parser(
        'inspect',
        help="Create new container from given image and access shell. You can use this to inspect image's content.")
    inspect.set_defaults(lxd_op='inspect')
    inspect.add_argument(
        'IMAGE',
        help="Name of image to inspect."
    )
    inspect.add_argument(
        '-i', '--internet',
        action='store_true',
        help='Get the Internet access in container even if image specifies no Internet access.'
    )
    inspect.add_argument(
        '-d', '--device',
        action='append',
        help="""Adds pair to device map. The argument (one pair) has to have format DEVICE=RESOURCE where DEVICE is full
        device specification from image and RESOURCE is resource mapped to it.
        """
    )
    inspect.add_argument(
        '-p', '--proxy',
        action='append',
        help="""Adds socket to be proxied to host. The argument has to be proto:address:port, for example:
        tcp:127.0.0.1:80. The port this is forwarded to is printed on to the terminal when container is started.
        """
    )

    return {
        None: parser,
        'clean': clean,
        'bootstrap': bootstrap,
        'inspect': inspect,
    }


def parse_deltatime(spec):
    """Parse relative time delta.
    """
    trans = {
        "m": lambda t: dateutil.relativedelta.relativedelta(minutes=t),
        "h": lambda t: dateutil.relativedelta.relativedelta(hours=t),
        "d": lambda t: dateutil.relativedelta.relativedelta(days=t),
        "w": lambda t: dateutil.relativedelta.relativedelta(weeks=t),
    }
    delta = dateutil.relativedelta.relativedelta()
    num = ""
    for char in spec:
        if char.isdigit():
            num += char
        elif char in trans:
            delta += trans[char](int(num))
            num = ""
        else:
            raise ValueError(f"Invalid character '{char}' in time delta specification: {spec}")
    return delta


def op_clean(args, _):
    """Handler for command line operation clean
    """
    removed = utils.clean(args.DELTA, dry_run=args.dry_run)
    if removed:
        print('\n'.join(removed))
    sys.exit(0)


def op_bootstrap(args, parser):
    """Handler for command line operation bootstrap
    """
    if not args.IMG and not args.all:
        parser.print_usage()
        sys.exit(1)
    success = True
    if args.all:
        success &= utils.bootstrap()
    success &= utils.bootstrap(args.IMG)
    sys.exit(0 if success else 1)


def op_inspect(args, parser):
    """Handler for command line operation inspect
    """
    kwargs = dict()
    if args.internet:
        kwargs["internet"] = True
    device_map = dict()
    if args.device:
        for device_spec in args.device:
            if '=' not in device_spec:
                parser.error(f"Invalid device specifier: {device_spec}")
            device, resource = device_spec.split('=', maxsplit=1)
            device_map[device] = resource

    connection = LXDConnection()
    with Container(connection, args.IMAGE, device_map=device_map, strict=False, **kwargs) as cont:
        if args.proxy:
            for proxy in args.proxy:
                el = proxy.split(':', maxsplit=2)
                if len(el) == 1:
                    args = {"port": el[0]}
                elif len(el) == 2:
                    args = {"address": el[0], "port": el[1]}
                else:
                    args = {"proto": el[0], "address": el[1], "port": el[2]}
                localport = cont.network.proxy_open(**args)
                print(f"Proxy '{proxy}' to: {localport}")
        sys.exit(subprocess.call(['lxc', 'exec', cont.name, '/bin/sh']))



def handle_args(args, parser_ret):
    handles = {
        'clean': op_clean,
        'bootstrap': op_bootstrap,
        'inspect': op_inspect,
    }
    if hasattr(args, 'lxd_op'):
        handles[args.lxd_op](args, parser_ret[args.lxd_op])
    else:
        parser_ret[None].print_usage()
        sys.exit(1)


def main():
    top_parser = argparse.ArgumentParser(description='NSFarm LXD management.')
    parser_ret = parser(top_parser)
    handle_args(top_parser.parse_args(), parser_ret)


if __name__ == '__main__':
    sys.argv[0] = "nsfarm.lxd"
    main()
