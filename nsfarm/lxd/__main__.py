import argparse
import subprocess
import sys

import dateutil.relativedelta
import pylxd

from . import Container, utils


def parser(upper_parser):
    subparsers = upper_parser.add_subparsers()

    clean = subparsers.add_parser("clean", help="Remove old and unused containers")
    clean.set_defaults(lxd_op="clean")
    clean.add_argument(
        "-i",
        "--images",
        action="store_true",
        help="Clean no longer used images.",
    )
    clean.add_argument(
        "-c",
        "--containers",
        action="store_true",
        help="Clean no longer used containers.",
    )
    clean.add_argument(
        "DELTA",
        nargs="?",
        default=dateutil.relativedelta.relativedelta(weeks=1),
        type=parse_deltatime,
        help="""Time delta for how long image should not be used to be cleaned (removed). In default if not specified
        '1w' is used. Format is expect to be a number with suffix. Supported suffixes are m(inute), h(our), d(ay) and
        w(eek). This applies only to images thus it has no effect if used with --containers.
        """,
    )
    clean.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Print what would be removed but do nothing.",
    )

    bootstrap = subparsers.add_parser("bootstrap", help="Bootstrap specific or all images")
    bootstrap.set_defaults(lxd_op="bootstrap")
    bootstrap.add_argument(
        "IMG",
        nargs="*",
        help="Name of image to bootstrap.",
    )
    bootstrap.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Bootstrap all images present instead of only listed ones.",
    )

    inspect = subparsers.add_parser(
        "inspect",
        help="Create new container from given image and access shell. You can use this to inspect image's content.",
    )
    inspect.set_defaults(lxd_op="inspect")
    inspect.add_argument(
        "IMAGE",
        help="Name of image to inspect.",
    )
    inspect.add_argument(
        "-i",
        "--internet",
        action="store_true",
        help="Get the Internet access in container even if image specifies no Internet access.",
    )
    inspect.add_argument(
        "-d",
        "--device",
        action="append",
        help="""Adds pair to device map. The argument (one pair) has to have format DEVICE=RESOURCE where DEVICE is full
        device specification from image and RESOURCE is resource mapped to it.
        """,
    )
    inspect.add_argument(
        "-p",
        "--proxy",
        action="append",
        help="""Adds socket to be proxied to host. The argument has to be proto:address:port, for example:
        tcp:127.0.0.1:80. The port this is forwarded to is printed on to the terminal when container is started.
        """,
    )

    return {
        None: upper_parser,
        "clean": clean,
        "bootstrap": bootstrap,
        "inspect": inspect,
    }


def parse_deltatime(spec):
    """Parse relative time delta."""
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
    """Handler for command line operation clean"""
    removed = []
    if args.images or not args.containers:
        removed += utils.clean_images(args.DELTA, dry_run=args.dry_run)
    if args.containers or not args.images:
        removed += utils.clean_containers(dry_run=args.dry_run)
    if removed:
        print("\n".join(removed))
    sys.exit(0)


def op_bootstrap(args, upper_parser):
    """Handler for command line operation bootstrap"""
    if not args.IMG and not args.all:
        upper_parser.print_usage()
        sys.exit(1)
    success = True
    if args.all:
        success &= utils.bootstrap()
    success &= utils.bootstrap(args.IMG)
    sys.exit(0 if success else 1)


def op_inspect(args, upper_parser):
    """Handler for command line operation inspect"""
    kwargs = {}
    if args.internet:
        kwargs["internet"] = True
    device_map = {}
    if args.device:
        for device_spec in args.device:
            if "=" not in device_spec:
                upper_parser.error(f"Invalid device specifier: {device_spec}")
            device, resource = device_spec.split("=", maxsplit=1)
            device_map[device] = resource

    lxd_client = pylxd.Client()
    with Container(lxd_client, args.IMAGE, device_map=device_map, strict=False, **kwargs) as cont:
        if args.proxy:
            for proxy in args.proxy:
                fields = proxy.split(":", maxsplit=2)
                if len(fields) == 1:
                    args = {"port": fields[0]}
                elif len(fields) == 2:
                    args = {"address": fields[0], "port": fields[1]}
                else:
                    args = {"proto": fields[0], "address": fields[1], "port": fields[2]}
                localport = cont.network.proxy_open(**args)
                print(f"Proxy '{proxy}' to: {localport}")
        sys.exit(subprocess.call(["lxc", "exec", cont.name, "/bin/sh"]))


def handle_args(args, parser_ret):
    handles = {
        "clean": op_clean,
        "bootstrap": op_bootstrap,
        "inspect": op_inspect,
    }
    if hasattr(args, "lxd_op"):
        handles[args.lxd_op](args, parser_ret[args.lxd_op])
    else:
        parser_ret[None].print_usage()
        sys.exit(1)


def main():
    top_parser = argparse.ArgumentParser(description="NSFarm LXD management.")
    parser_ret = parser(top_parser)
    handle_args(top_parser.parse_args(), parser_ret)


if __name__ == "__main__":
    sys.argv[0] = "nsfarm.lxd"
    main()
