import time
import random
import string
import pathlib
import configparser
import pytest
import nsfarm.board
import nsfarm.cli
import nsfarm.lxd
import nsfarm.target


def pytest_addoption(parser):
    parser.addoption(
        "-T", "--target",
        help="Run tests on specified TARGET.",
        metavar="TARGET",
    )
    parser.addoption(
        "--board",
        help="Run tests on one of the targets with given BOARD unless exact target is specified.",
        metavar="BOARD",
    )
    parser.addoption(
        "-C", "--targets-config",
        help="Path to configuration file with additional targets.",
        metavar="PATH",
    )
    parser.addoption(
        "-B", "--branch",
        default="hbk",
        help="Run tests for specified Turris OS BRANCH.",
        metavar="BRANCH",
    )


def pytest_configure(config):
    # Parse target configuration
    targets = nsfarm.target.Targets(config.getoption("-C") or (), rootdir=config.rootdir)
    # Set target configuration
    target_name = config.getoption("-T")
    if target_name is None:
        try:
            target_name = next(targets.filter(board=config.getoption("--board")))
        except StopIteration:
            pass
    if target_name in targets:  # Targets might not be set for example with --help argument
        setattr(config, "target_config", targets[target_name])
    # Set target branch
    branch = config.getoption("-B")
    setattr(config, "target_branch", branch)

    # Store configuration to metadata (basically just for pytest-html)
    if hasattr(config, '_metadata'):
        config._metadata.update({
            'NSFarm-Target': target_name,
            'NSFarm-TurrisBranch': branch,
        })


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

@pytest.fixture(scope="session", name="board")
def fixture_board(request):
    """Brings board on. Nothing else.
    This is top most fixture for board. It returns board handle.
    """
    brd = nsfarm.board.get_board(request.config.target_config)
    brd.power(True)
    request.addfinalizer(lambda: brd.power(False))
    return brd


@pytest.fixture(scope="session", name="lxd")
def fixture_lxd():
    """Provides access to nsfarm.lxd.LXDConnection instance.
    """
    return nsfarm.lxd.LXDConnection()


@pytest.fixture(scope="session", name="wan")
def fixture_wan(request):
    """Top level fixture used to share WAN interface handler.
    """
    return nsfarm.lxd.NetInterface("wan", request.config.target_config.wan)


@pytest.fixture(scope="session", name="lan1", params=[pytest.param("lan1", marks=pytest.mark.lan1)])
def fixture_lan1(request):
    """Top level fixture used to share LAN1 interface handler.
    """
    return nsfarm.lxd.NetInterface("lan", request.config.target_config.lan1)


########################################################################################################################
# Boot and setup fixtures ##############################################################################################

@pytest.fixture(name="board_serial", scope="session")
def fixture_board_serial(request, lxd, board, wan):
    """Boot board to Shell.
    Provides instance of nsfarm.cli.Shell()
    """
    request.addfinalizer(lambda: board.reset(True))
    return board.bootup(lxd, wan, request.config.target_branch)


@pytest.fixture(name="board_root_password", scope="session")
def fixture_board_root_password(request, board_serial):
    """Sets random password for user root.
    Returns configured random password
    """
    password = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
    board_serial.run(f"echo 'root:{password}' | chpasswd")
    request.addfinalizer(lambda: board_serial.run("passwd --delete root"))
    return password


@pytest.fixture(name="client_board", scope="module")
def fixture_client_board(board_serial, board_root_password, lan1_client):
    """Starts client on LAN1 and connect to board using SSH.
    Provides instance of nsfarm.cli.Shell() connected to board shell using SSH trough client container.

    This is prefered over serial console as kernel logs are preferably printed there and that can break CLI machinery.
    """
    # Let's have syslog on serial console as well as kernel log
    board_serial.command('while ! [ -f /var/log/messages ]; do sleep 1; done && tail -f /var/log/messages')
    # Now spawn client container and connect
    nsfarm.cli.Shell(lan1_client.pexpect()).run('wait4network')
    pexp = lan1_client.pexpect(['ssh', '-q', '192.168.1.1'])
    pexp.expect_exact("root@192.168.1.1's password:")
    pexp.sendline(board_root_password)
    pexp.expect_exact("root@turris:")
    yield nsfarm.cli.Shell(pexp, flush=False)  # TODO drop this flush disable when it works
    # Kill tail -f on serial console
    board_serial.send('\x03')
    board_serial.prompt()


########################################################################################################################
# Common containers ####################################################################################################

@pytest.fixture(name="lan1_client", scope="module")
def fixture_lan1_client(lxd, lan1):
    """Starts client container on LAN1 and provides it.
    """
    with nsfarm.lxd.Container(lxd, 'client', devices=[lan1, ], internet=False) as container:
        yield container


########################################################################################################################
# Standard configuration ###############################################################################################

@pytest.fixture(name="basic_isp", scope="module")
def fixture_basic_isp(lxd, board, client_board, wan):
    """Basic config we consider general. It provides you with configured WAN.

    Returns handle for ISP container on WAN interface.
    """
    # TODO what about other settings that are part of guide
    with nsfarm.lxd.Container(lxd, 'isp-common', devices=[wan, ]) as container:
        client_board.run("uci set network.wan.proto='static'")
        client_board.run("uci set network.wan.ipaddr='172.16.1.42'")
        client_board.run("uci set network.wan.netmask='255.240.0.0'")
        client_board.run("uci set network.wan.gateway='172.16.1.1'")
        client_board.run("uci set network.wan.dns='172.16.1.1'")
        client_board.run("uci commit network")
        client_board.run("/etc/init.d/network restart")
        client_board.run(f"while ! ip link show {board.wan} | grep -q ' state UP '; do sleep 1; done")
        time.sleep(3)  # Wait just a bit to ensure that network is up and running
        yield container
        client_board.run("uci set network.wan.proto='none'")
        client_board.run("uci delete network.wan.ipaddr")
        client_board.run("uci delete network.wan.netmask")
        client_board.run("uci delete network.wan.gateway")
        client_board.run("uci delete network.wan.dns")
        client_board.run("uci commit network")


########################################################################################################################
# Reports enrichment ###################################################################################################

def pytest_report_header(config):
    return (
        f"nsfarm-target: {config.target_config if config.getoption('verbose') > 0 else config.target_config.name}",
        f"nsfarm-branch: {config.target_branch}",
    )


@pytest.fixture(scope="session", autouse=True)
def log_target_to_testsuite_property(request, record_testsuite_property):
    """Include target and branch in test results as global properties.
    """
    record_testsuite_property("nsfarm-target", request.config.target_config.name)
    record_testsuite_property("nsfarm-branch", request.config.target_branch)
