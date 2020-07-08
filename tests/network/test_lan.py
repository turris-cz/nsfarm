"""Test LAN access of Internet and software on LAN side.
"""
import time
import pytest
import nsfarm.lxd
from . import common
# pylint: disable=no-self-use


def _apply(client_board):
    client_board.run("uci commit network")
    client_board.run("/etc/init.d/network restart")
    time.sleep(5)  # TODO drop this as this is just to prevent problems with kernel log in console
    client_board.run("while ! ip route | grep -q default; do sleep 1; done")  # Wait for default route


class TestInternet(common.InternetTests):
    """Test WAN with network settings configured statically.
    """

    @pytest.fixture(scope="class", autouse=True)
    def client(self, basic_isp, lan1_client):
        """With basic router config and client is client container.
        """
        yield nsfarm.cli.Shell(lan1_client.pexpect())
