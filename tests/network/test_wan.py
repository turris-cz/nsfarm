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
            with nsfarm.setup.uplink.DHCPv4(client_board) as wan:
                wan.wait4route()
                yield client_board


@pytest.mark.skip("The configuration here removes what is done in fixture board_wan and this removes its revert")
class TestPPPoE(common.InternetTests):
    """Test of PPPoE"""

    @pytest.fixture(name="client", scope="class", autouse=True)
    def fixture_client(self, lxd_client, device_map, client_board):
        with nsfarm.lxd.Container(lxd_client, "isp-pppoe", device_map):
            with nsfarm.setup.uplink.PPPoE(client_board) as wan:
                wan.wait4ping()
                yield client_board
