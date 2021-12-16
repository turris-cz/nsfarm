import argparse
import contextlib
import sys

import pylxd

from .. import lxd, setup
from ..board import get_board
from . import Targets


def parser(upper_parser):
    subparsers = upper_parser.add_subparsers()

    plist = subparsers.add_parser("list", help="List avalable targets for NSFarm")
    plist.set_defaults(target_op="list")
    plist.add_argument(
        "-a",
        "--all",
        action="store_true",
        default=False,
        help="List all targets not just available ones",
    )
    plist.add_argument(
        "-b",
        "--board",
        help="Limit to specific board type",
    )
    plist.add_argument(
        "-s",
        "--serial",
        action="store_true",
        help="Limit to only targets with serial console",
    )

    verify = subparsers.add_parser("verify", help="Verify that target is correctly configured.")
    verify.set_defaults(target_op="verify")
    verify.add_argument(
        "TARGET",
        nargs="*",
        help="Name of target to verify configuration of.",
    )

    uboot = subparsers.add_parser("uboot", help="Access uboot trough serial console on given target")
    uboot.set_defaults(target_op="uboot")
    uboot.add_argument(
        "TARGET",
        nargs=1,
        help="Name of target to access.",
    )

    boot = subparsers.add_parser("boot", help="Boot system trough serial console on given target")
    boot.set_defaults(target_op="boot")
    boot.add_argument(
        "TARGET",
        nargs=1,
        help="Name of target to access.",
    )
    boot.add_argument(
        "-B",
        "--branch",
        default="hbk",
        help="Run system from specified Turris OS BRANCH instead of default hbk.",
        metavar="BRANCH",
    )
    boot.add_argument(
        "--no-client",
        action="store_true",
        help="Do not start client container alongside the boot to allow simple access on board.",
    )
    boot.add_argument(
        "--no-isp",
        action="store_true",
        help="Do not provide ISP container with DHCP server on WAN.",
    )
    boot.add_argument(
        "--default",
        action="store_true",
        help="In default we try to improve experience by applying some configuration. This disables that.",
    )

    return {
        None: upper_parser,
        "list": plist,
        "verify": verify,
        "uboot": uboot,
        "boot": boot,
    }


def op_list(args, upper_parser):
    """Handler for command line operation list."""
    targets = Targets()
    for name, target in targets.items():
        if not args.all and not target.is_available():
            continue
        if args.board and target.board not in args.board:
            continue
        if args.serial and not target.is_configured("serial"):
            continue
        print(target.name)
    sys.exit(0)


def op_verify(args, upper_parser):
    """Handler for command line operation verify."""
    targets = Targets()
    toverify = args.TARGET
    if len(toverify) == 0:
        toverify = list(targets.keys())
    result = True
    for target in toverify:
        if target not in targets:
            upper_parser.error(f"Target does not exist: {target}")
        correct = targets[target].check()
        print(f"{target}: {correct}")
        result = result and correct

    sys.exit(0 if result else 1)


def op_uboot(args, upper_parser):
    """Handler for command line operation uboot."""
    targets = Targets()
    target_name = args.TARGET[0]
    if target_name not in targets:
        upper_parser.error(f"Target does not exist: {target_name}")
    board = get_board(targets[target_name])
    uboot_cli = board.uboot()
    uboot_cli.mterm()
    sys.exit(0)


@contextlib.contextmanager
def boot_isp(args, lxd_client, target):
    if args.no_isp:
        return
    with lxd.Container(lxd_client, "isp-dhcp", target.device_map()) as isp:
        yield isp


@contextlib.contextmanager
def boot_client(args, lxd_client, target):
    if args.no_client:
        return
    with lxd.Container(lxd_client, "client", {"net:lan": target.device_map()["net:lan1"]}) as client:
        yield client


def op_boot(args, parser):
    """Handler for command line operation boot."""
    targets = Targets()
    target_name = args.TARGET[0]
    if target_name not in targets:
        parser.error(f"Target does not exist: {target_name}")
    target = targets[target_name]
    board = get_board(target)
    lxd_client = pylxd.Client()
    shell = board.bootup(lxd_client, args.branch)
    shell.run("cd")
    with boot_isp(args, lxd_client, target) as isp:
        with boot_client(args, lxd_client, target) as client:
            if not args.default:  # Perform various setups to have system in more usable state
                setup.utils.RootPassword(shell, "turris").revert_not_needed()
                if isp is not None:
                    isp.shell.run("wait4network")
                    setup.uplink.DHCPv4(shell).revert_not_needed()
                if client is not None:
                    setup.utils.SSHKey(client.shell, shell).revert_not_needed()
            shell.mterm()
    sys.exit(0)


def handle_args(args, parser_ret):
    handles = {
        "list": op_list,
        "verify": op_verify,
        "uboot": op_uboot,
        "boot": op_boot,
    }
    if hasattr(args, "target_op"):
        handles[args.target_op](args, parser_ret[args.target_op])
    else:
        parser_ret[None].print_usage()
        sys.exit(1)


def main():
    top_parser = argparse.ArgumentParser(description="Targets of NSFarm listing and management.")
    parser_ret = parser(top_parser)
    handle_args(top_parser.parse_args(), parser_ret)


if __name__ == "__main__":
    sys.argv[0] = "nsfarm.config"
    main()
