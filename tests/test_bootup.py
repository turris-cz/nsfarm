"""These are test that check that everything we need is running after boot. This does simple and quick tests to catch
general errors such as disabled core services.
"""
import time

import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.toolbox import service_is_running

from . import mark


@pytest.mark.deploy
def test_syslog_ng(client_board):
    """Check that syslog-ng is running by checking if there is /var/log/messages (default log output)."""
    client_board.run("[ -f /var/log/messages ]")


@pytest.mark.deploy
@pytest.mark.parametrize(
    "process",
    [
        "crond",
        "dnsmasq",
        pytest.param("kresd", marks=mark.kresd),
        pytest.param("unbound", marks=mark.unbound),
        "lighttpd",
        "mosquitto",
        "netifd",
        "odhcpd",
        "rpcd",
        "sshd",
        "syslog-ng",
        "ubusd",
    ],
)
def test_processes(client_board, process):
    """Check that various essential processes are running."""
    client_board.run(f"pgrep -x '{process}' || pgrep -a \"$(which '{process}')\"")


basic_services = [
    "atd",
    "cron",
    "dnsmasq",
    "foris-controller",
    "foris-ws",
    "fosquitto",
    "haveged",
    "lighttpd",
    "network",
    "odhcpd",
    "rpcd",
    "sshd",
    "syslog-ng",
    "sysntpd",
    "umdns",
]


@pytest.mark.deploy
@pytest.mark.parametrize(
    "service",
    basic_services
    + [
        pytest.param("kresd", marks=mark.kresd),
        pytest.param("unbound", marks=mark.unbound),
    ],
)
def test_running_services(client_board, service):
    """Check that various essential services are running."""
    assert service_is_running(service, client_board)


@pytest.mark.deploy
@pytest.mark.parametrize(
    "service",
    basic_services
    + [
        "boot",
        "done",
        "gpio_switch",
        "led",
        pytest.param("mox_autosetup", marks=mark.only_mox),
        pytest.param("rainbow", marks=mark.rainbow),
        "resolver",
        pytest.param("setup_led", marks=mark.only_turris1x),
        "srv",
        "sysctl",
        "sysfixtime",
        "sysfsutils",
        "system",
        "ucitrack",
        "umount",
        pytest.param("update_mac", marks=mark.only_turris1x),
        "updater-journal-recover",
        "urandom_seed",
        pytest.param("zram", marks=mark.low_ram),
    ],
)
def test_services(client_board, service):
    """Check that various essential services are enabled."""
    client_board.run(f"/etc/init.d/{service} enabled")


@pytest.mark.deploy
def test_lighttpd(lan1_client):
    """Test that there is access to router interface."""
    pexp = Shell(lan1_client.pexpect())
    pexp.run("wget 192.168.1.1 && rm index.html")


@pytest.mark.deploy
def test_no_wan(client_board):
    """Wan interface should be in default configured to none and thus disabled."""
    client_board.run("uci get network.wan.proto")
    assert client_board.output == "none"


class TestNoInternetAccess:
    """The router should not have WAN interface configured to any valid setting as we want to force users to first go
    through first setup guide and set password there.
    """

    @pytest.fixture(scope="class", autouse=True)
    def fixture_dhcp_isp(self, lxd_client, device_map, client_board):
        """This provides DHCP server on WAN interface the router could use to autoconfigure WAN if it would want to."""
        with Container(lxd_client, "isp-dhcp", device_map) as container:
            container.shell.run("wait4network")
            client_board.run("/etc/init.d/network restart")  # Trigger network restart to force potential renew now
            # Unfortunatelly we can't wait for router to pickup address as technically it should not. Instead we wait
            # some amount of time we can expect it would picked up address from DHCP.
            time.sleep(10)
            yield container

    @pytest.mark.parametrize("ipv", ["4", "6"])
    def test_no_internet_access(self, client_board, ipv):
        """Although test_no_wan checks if wan is not configured it does not mean that some automatic function might not
        configure WAN. This checks that we really do not have the Internet access.
        It is reasonable assumption that without default route there is no Internet access so it should be enough to
        check if there is no default route.
        """
        assert client_board.run(f"ip -{ipv} route | grep -F 'default via'", None) == 1
