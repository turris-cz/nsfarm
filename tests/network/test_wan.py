"""Various configurations of WAN and appropriate tests.

This checks if we are able to support various ISP configurations.
"""
import time
import pytest
import nsfarm.lxd
from . import common
# pylint: disable=no-self-use

# TODO: add support for IPV6, currently we only test IPv4


def _apply(client_board):
    client_board.run("uci commit network")
    client_board.run("/etc/init.d/network restart")
    client_board.run("while ! ip route | grep -q default; do sleep 1; done")  # Wait for default route


class TestStatic(common.InternetTests):
    """Test WAN with network settings configured statically.
    """

    @pytest.fixture(scope="class", autouse=True)
    def configure(self, client_board, wan):
        """Configure WAN to use static IP
        """
        with nsfarm.lxd.Container('isp-common', devices=[wan, ]) as container:
            # TODO implement some utility class to set and revert uci configs on router
            client_board.run("uci set network.wan.proto='static'")
            client_board.run("uci set network.wan.ipaddr='172.16.1.42'")
            client_board.run("uci set network.wan.netmask='255.240.0.0'")
            client_board.run("uci set network.wan.gateway='172.16.1.1'")
            client_board.run("uci set network.wan.dns='1.1.1.1'")  # TODO configure to ISP
            _apply(client_board)
            yield container
            client_board.run("uci set network.wan.proto='none'")
            client_board.run("uci delete network.wan.ipaddr")
            client_board.run("uci delete network.wan.netmask")
            client_board.run("uci delete network.wan.gateway")
            client_board.run("uci delete network.wan.dns")
            client_board.run("uci commit network")


class TestDHCP(common.InternetTests):
    """Test WAN with network settings provided by DHCP server.
    """

    @pytest.fixture(scope="class", autouse=True)
    def configure(self, board, client_board, wan):
        """Configure WAN to use DHCP
        """
        with nsfarm.lxd.Container('isp-dhcp', devices=[wan, ]) as container:
            client_board.run("uci set network.wan.proto='dhcp'")
            client_board.run("uci commit network")
            _apply(client_board)
            yield container
            client_board.run("uci set network.wan.proto='none'")
            client_board.run("uci commit network")
