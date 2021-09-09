"""Test LAN access of Internet and software on LAN side."""
import pytest

import nsfarm
from nsfarm.toolbox.alpine import network_connect

from . import common

# pylint: disable=no-self-use


@pytest.fixture(name="dhcp_client", scope="module")
def fixture_dchp_client(lxd_client, device_map):
    """Simple client with address obtained via DHCP"""
    with nsfarm.lxd.Container(lxd_client, "client-dhcp", {"net:lan": device_map["net:lan1"]}) as container:
        container.shell.run("wait4network")
        yield container


@pytest.mark.deploy
class TestLAN:
    """Test to test basic connection to router. Tests TCP connection.

    This test does not use board_client connection, therefore, it may find
    issues with connection to the router.
    """

    ROUTER_IP = "192.168.1.1"

    @pytest.mark.parametrize("port", [22, 80, 443])
    def test_TCP(self, dhcp_client, board_serial, port):
        """Connects to port 22, 80, 443 via TCP. Using netcat. These ports should be opened by default."""
        assert network_connect(
            dhcp_client.shell, target=self.ROUTER_IP, port=port
        ), f"Router(DUT) cannot be accessed by port {port} via TCP"


@pytest.mark.deploy
class TestInternet(common.InternetTests):
    """Test WAN with network settings configured statically."""

    @pytest.fixture(scope="class", autouse=True)
    def client(self, board_wan, dhcp_client):
        """With basic router config and client is client container."""
        shell = nsfarm.cli.Shell(dhcp_client.pexpect())
        shell.run("wait4network")
        yield shell
