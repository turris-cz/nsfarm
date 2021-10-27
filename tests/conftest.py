import collections.abc
import random
import string
import time
import typing

import pexpect
import pylxd
import pytest

import nsfarm.board
import nsfarm.cli
import nsfarm.lxd
import nsfarm.setup
import nsfarm.target
import nsfarm.web

from . import mark


def pytest_addoption(parser):
    parser.addoption(
        "--board",
        help="Run tests on one of the targets with given BOARD unless exact target is specified.",
        metavar="BOARD",
    )
    parser.addoption(
        "-B",
        "--branch",
        default="hbk",
        help="Run tests for specified Turris OS BRANCH.",
        metavar="BRANCH",
    )


def pytest_configure(config):
    mark.register_marks(config)
    # Select target configuration unless explicitly specified from top level conftest
    if config.target_config is None:
        try:
            # If there was no target selection then we chose one
            # Note: We can run tests only on one target. This way we force selftests to run on our target only.
            setattr(
                config,
                "target_config",
                config.targets[next(config.targets.filter(board=config.getoption("--board")))],
            )
        except StopIteration:
            pass
    # Set target branch
    branch = config.getoption("-B")
    setattr(config, "target_branch", branch)
    # Store configuration to metadata (basically just for pytest-html)
    if hasattr(config, "_metadata"):
        config._metadata.update(
            {
                "NSFarm-Target": config.target_config.name if config.target_config else None,
                "NSFarm-TurrisBranch": branch,
            }
        )


def pytest_sessionstart(session):
    if not hasattr(session.config, "target_config"):
        raise pytest.UsageError("There is no available test target.")


def pytest_runtest_setup(item):
    def check_board(boards, expected):
        board = item.config.target_config.board
        if (board in boards.args) is expected:
            pytest.skip(f"test is not compatible with target: {board}")

    for boards in item.iter_markers(name="board"):
        check_board(boards, False)
    for boards in item.iter_markers(name="not_board"):
        check_board(boards, True)
    for conn in ("lan1", "lan2"):
        if item.get_closest_marker(conn) is not None and not item.config.target_config.is_configured(conn):
            pytest.skip(f"test requires connection: {conn}")


########################################################################################################################
# Resources shared among all tests #####################################################################################


@pytest.fixture(name="board", scope="session")
def fixture_board(request):
    """Brings board on. Nothing else.
    This is top most fixture for board. It provides board handle.
    """
    brd = nsfarm.board.get_board(request.config.target_config)
    brd.power(True)
    yield brd
    brd.power(False)


@pytest.fixture(name="lxd_client", scope="session")
def fixture_lxd_client():
    """Provides access to pylxd.Client() instance."""
    return pylxd.Client()


@pytest.fixture(name="device_map", scope="session")
def fixture_device_map(request):
    """Provides easier access to device map generated by target."""
    return request.config.target_config.device_map()


########################################################################################################################
# Boot and setup fixtures ##############################################################################################


@pytest.fixture(name="board_serial", scope="package")
def fixture_board_serial(lxd_client, request, board):
    """Boot board to Shell.
    Provides instance of nsfarm.cli.Shell()
    """
    request.addfinalizer(lambda: board.reset(True))
    serial = board.bootup(lxd_client, request.config.target_branch)
    serial.run("cd")  # move to /root from / as that is in general expected and consistent with SSH
    return serial


@pytest.fixture(name="board_root_password", scope="package")
def fixture_board_root_password(request, board_serial):
    """Sets random password for user root and thus it unlocks it (note that it is locked by default).
    Returns configured random password
    """
    board_serial.run("grep '^root:!:' /etc/shadow")  # verify that account is locked
    with nsfarm.setup.utils.RootPassword(board_serial) as pass_setup:
        yield pass_setup.password


@pytest.fixture(name="board_access", scope="package")
def fixture_board_access(board, board_serial, lan1_client, board_root_password):
    """Starts client on LAN1 and provides a way to connect to board using SSH.
    Provides function that opens new shell instance or runs provided command trough SSH.

    This is prefered over serial console as kernel logs are preferably printed there and that can break CLI machinery.
    """

    def spawn(
        command: typing.Optional[collections.abc.Iterable[str]] = None,
    ) -> typing.Union[nsfarm.cli.Shell, pexpect.spawn]:
        """Open new connection to board using SSH or run given command"""
        ssh = ["ssh", "-q", "192.168.1.1"]
        if command is None:
            return nsfarm.cli.Shell(lan1_client.pexpect(ssh))
        return lan1_client.pexpect(ssh + list(command))

    with nsfarm.setup.utils.SSHKey(lan1_client.shell, board_serial):
        # Let's have syslog on serial console
        board_serial.command("while ! [ -f /var/log/messages ]; do sleep 1; done && tail -f /var/log/messages")
        board.set_serial_flush(True)

        lan1_client.shell.run("wait4network")  # Make sure that client can access the router
        yield spawn

        board.set_serial_flush(False)
        board_serial.ctrl_c()  # Terminate tail -f on serial console
        board_serial.prompt()


class BoardShell(nsfarm.cli.Shell):
    """Special Shell instance that is able to reconnect. That is to replace connection with the new one."""

    def __init__(self, board_access):
        self._board_access = board_access
        self.reconnect()

    def reconnect(self):
        """Open the new connection instead of the existing one."""
        super().__init__(self._board_access([]))


@pytest.fixture(name="board_access_for_fixture", scope="package")
def fixture_board_access_for_fixture(board_access) -> BoardShell:
    """This is single instance of cli.Shell received from board_access that should be used in fixtures only.
    The reason for this is that we have load of fixtures before we ever get to single tests and spawning shell for every
    single one of the would get spammy very fast. We expect fixtures to be well behaved and thus we give them one shared
    shell.

    This returns special variant of cli.Shell that has one additional method reconnect(). It allows you to request the
    new instance and that way replace the existing one.
    """
    return BoardShell(board_access)


@pytest.fixture(name="client_board", scope="package")
def fixture_client_board(board_access):
    """Provides Shell instance on board trough board_access.

    This is obsolete fixture and should no longer be used in new tests. Instead create new shell instance for every test
    using function provided by board_access fixture.
    """
    return board_access()


########################################################################################################################
# Common containers ####################################################################################################


@pytest.fixture(name="isp_container", scope="package")
def fixture_isp_container(lxd_client, device_map):
    """Minimal ISP container used to provide the Internet access for the most of the tests."""
    with nsfarm.lxd.Container(lxd_client, "isp-common", device_map) as container:
        container.shell.run("wait4network")
        yield container


@pytest.fixture(name="lan1_client", scope="package")
def fixture_lan1_client(lxd_client, device_map):
    """Starts client container with static IP address 192.168.1.10/24 on LAN1 and provides it."""
    with nsfarm.lxd.Container(lxd_client, "client", {"net:lan": device_map["net:lan1"]}) as container:
        container.shell.run("wait4boot")
        yield container


@pytest.fixture(name="lan1_webclient", scope="package")
def fixture_lan1_webclient(lxd_client, device_map):
    """Starts web-client container on LAN1 and provides it."""
    with nsfarm.web.Container(lxd_client, {"net:lan": device_map["net:lan1"]}) as container:
        container.shell.run("wait4boot")
        yield container


########################################################################################################################
# Standard configuration ###############################################################################################


@pytest.fixture(name="board_wan", scope="package")
def fixture_board_wan(client_board, isp_container):
    """Basic config Internet configuration usable for most of the tests.
    This configures static IP through ips_container.
    Returns wan IPv4 address of WAN interface.
    """
    wan_ip = "172.16.1.142"
    client_board.run("uci set network.wan.proto='static'")
    client_board.run(f"uci set network.wan.ipaddr='{wan_ip}'")
    client_board.run("uci set network.wan.netmask='255.240.0.0'")
    client_board.run("uci set network.wan.gateway='172.16.1.1'")
    client_board.run("uci set network.wan.dns='172.16.1.1'")
    client_board.run("uci commit network")
    client_board.run("/etc/init.d/network restart")
    client_board.run("while ! ping -c1 -w1 172.16.1.1 >/dev/null; do true; done")
    yield wan_ip
    client_board.run("uci set network.wan.proto='none'")
    client_board.run("uci delete network.wan.ipaddr")
    client_board.run("uci delete network.wan.netmask")
    client_board.run("uci delete network.wan.gateway")
    client_board.run("uci delete network.wan.dns")
    client_board.run("uci commit network")


@pytest.fixture(name="updater_branch", scope="package")
def fixture_updater_branch(request, client_board):
    """Setup target branch to updater.
    This is required as not in all branches is the target updater branch the build branch.
    """
    nsfarm.setup.updater.UpdaterBranch(client_board, request.config.target_branch).request(request)
    return request.config.target_branch


########################################################################################################################
# Reports enrichment ###################################################################################################


def pytest_report_header(config):
    return (
        f"nsfarm-target: {config.target_config if config.getoption('verbose') > 0 else config.target_config.name}",
        f"nsfarm-branch: {config.target_branch}",
    )


@pytest.fixture(scope="package", autouse=True)
def log_target_to_testsuite_property(request, record_testsuite_property):
    """Include target and branch in test results as global properties."""
    record_testsuite_property("nsfarm-target", request.config.target_config.name)
    record_testsuite_property("nsfarm-branch", request.config.target_branch)
