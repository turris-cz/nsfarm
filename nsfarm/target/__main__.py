import sys
import argparse
from . import Targets
from ..board import get_board
from ..mterm import mterm


def parser(parser):
    subparsers = parser.add_subparsers()

    plist = subparsers.add_parser('list', help='List avalable targets for NSFarm')
    plist.set_defaults(target_op='list')
    plist.add_argument(
        '-a', '--all',
        action="store_true",
        default=False,
        help="List all targets not just available ones"
    )
    plist.add_argument(
        '-b', '--board',
        help="Limit to specific board type"
    )
    plist.add_argument(
        '-s', '--serial',
        action='store_true',
        help="Limit to only targets with serial console"
    )

    verify = subparsers.add_parser('verify', help='Verify that target is correctly configured.')
    verify.set_defaults(target_op='verify')
    verify.add_argument(
        'TARGET',
        nargs='*',
        help="Name of target to verify configuration of."
    )

    uboot = subparsers.add_parser('uboot', help='Access uboot trough serial console on given target')
    uboot.set_defaults(target_op='uboot')
    uboot.add_argument(
        'TARGET',
        nargs=1,
        help="Name of target to access."
    )

    return {
        None: parser,
        'list': plist,
        'verify': verify,
        'uboot': uboot,
    }


def op_list(args, parser):
    """Handler for command line operation list.
    """
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


def op_verify(args, parser):
    """Handler for command line operation verify.
    """
    targets = Targets()
    toverify = args.TARGET
    if len(toverify) == 0:
        toverify = list(targets.keys())
    result = True
    for target in toverify:
        if target not in targets:
            parser.error(f"Target does not exist: {target}")
        correct = targets[target].check()
        print(f"{target}: {correct}")
        result = result and correct
    sys.exit(0 if result else 1)


def op_uboot(args, parser):
    """Handler for command line operation uboot.
    """
    targets = Targets()
    target_name = args.TARGET[0]
    if target_name not in targets:
        parser.error(f"Target does not exist: {target_name}")
    board = get_board(targets[target_name])
    uboot_cli = board.uboot()
    uboot_cli.mterm()
    sys.exit(0)


def handle_args(args, parser_ret):
    handles = {
        'list': op_list,
        'verify': op_verify,
        'uboot': op_uboot,
    }
    if hasattr(args, 'target_op'):
        handles[args.target_op](args, parser_ret[args.target_op])
    else:
        parser_ret[None].print_usage()
        sys.exit(1)


def main():
    top_parser = argparse.ArgumentParser(description='Targets of NSFarm listing and management.')
    parser_ret = parser(top_parser)
    handle_args(top_parser.parse_args(), parser_ret)


if __name__ == '__main__':
    sys.argv[0] = "nsfarm.config"
    main()
