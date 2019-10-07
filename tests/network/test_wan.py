"""Various configurations of WAN and appropriate tests.

This checks if we are able to support various ISP configurations.
"""
import time
import pytest
import nsfarm.lxd
from . import common
# pylint: disable=no-self-use

# TODO: add support for IPV6, currently we only test IPv4


def _apply(board_shell):
    board_shell.run("uci commit network")
    board_shell.run("/etc/init.d/network restart")
    time.sleep(5)  # TODO drop this as this is just to prevent problems with kernel log in console
    board_shell.run("while ! ip route | grep -q default; do sleep 1; done")  # Wait for default route


class TestStatic(common.InternetTests):
    """Test WAN with network settings configured statically.
    """

    @pytest.fixture(scope="class", autouse=True)
    def configure(self, board_shell, wan):
        """Configure WAN to use static IP
        """
        with nsfarm.lxd.Container('isp-common', devices=[wan, ]) as container:
            # TODO implement some utility class to set and revert uci configs on router
            board_shell.run("uci set network.wan.proto='static'")
            board_shell.run("uci set network.wan.ipaddr='172.16.1.42'")
            board_shell.run("uci set network.wan.netmask='255.240.0.0'")
            board_shell.run("uci set network.wan.gateway='172.16.1.1'")
            board_shell.run("uci set network.wan.dns='1.1.1.1'")  # TODO configure to ISP
            _apply(board_shell)
            yield container
            board_shell.run("uci set network.wan.proto='none'")
            board_shell.run("uci delete network.wan.ipaddr")
            board_shell.run("uci delete network.wan.netmask")
            board_shell.run("uci delete network.wan.gateway")
            board_shell.run("uci delete network.wan.dns")
            board_shell.run("uci commit network")


class TestDHCP(common.InternetTests):
    """Test WAN with network settings provided by DHCP server.
    """

    @pytest.fixture(scope="class", autouse=True)
    def configure(self, board, board_shell, wan):
        """Configure WAN to use DHCP
        """
        with nsfarm.lxd.Container('isp-dhcp', devices=[wan, ]) as container:
            board_shell.run("uci set network.wan.proto='dhcp'")
            board_shell.run("uci commit network")
            _apply(board_shell)
            yield container
            board_shell.run("uci set network.wan.proto='none'")
            board_shell.run("uci commit network")
