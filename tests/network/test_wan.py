"""Various configurations of WAN and appropriate tests.

This checks if we are able to support various ISP configurations.
Client is here a server on WAN side.
"""
import ipaddress
import logging

import pytest

import nsfarm.lxd
import nsfarm.setup

from . import common

# pylint: disable=no-self-use

# TODO: add support for IPV6, currently we only test IPv4


@pytest.fixture(scope="module", autouse=True)
def fixture_wait4network(board_wan):
    """We switch uplink configuration here but other tests rely on working uplink connection so we have to make sure
    before we leave this module that it really works.
    """
    yield
    board_wan.wait4network()


@pytest.mark.deploy
class TestStatic(common.InternetTests):
    """Test WAN with network settings configured statically."""

    @pytest.fixture(name="client", scope="class", autouse=True)
    def fixture_client(self, client_board, board_wan):
        """Configure WAN to use static IP"""
        yield client_board


@pytest.mark.deploy
class TestDHCP(common.InternetTests):
    """Test WAN with network settings provided by DHCP server."""

    @pytest.fixture(name="client", scope="class", autouse=True)
    def fixture_client(self, lxd_client, device_map, client_board):
        """Configure WAN to use DHCP"""
        with nsfarm.lxd.Container(lxd_client, "isp-dhcp", device_map):
            with nsfarm.setup.uplink.DHCPv4(client_board):
                yield client_board


class TestPPPoE(common.InternetTests):
    """Test of PPPoE"""

    @pytest.fixture(name="client", scope="class", autouse=True)
    def fixture_client(self, lxd_client, device_map, client_board):
        """Configure WAN to use PPPoE"""
        with nsfarm.lxd.Container(lxd_client, "isp-pppoe", device_map):
            with nsfarm.setup.uplink.PPPoE(client_board):
                yield client_board
