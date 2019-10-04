"""Common base tests definitions.

These are implementation of tests that are run in environments environments and this is a way to share the definition.
"""
import pytest
# pylint: disable=no-self-use

class InternetTests:
    """Tests for checking if connection to Internet is appropriate.
    """

    @pytest.mark.parametrize("server", [
        "172.16.1.1",  # ISP gateway
        "217.31.205.50"  # nic.cz
    ])
    def test_ping(self, board_shell, server):
        """Ping various IPv4 addresses.

        We send only one ICMP packet to not flood.
        """
        board_shell.run("ping -c 1 '{}'".format(server))

    @pytest.mark.parametrize("server", ["nic.cz", "turris.cz", "google.com"])
    def test_ping_name(self, board_shell, server):
        """Ping various IPv4 address using DNS record.
        """
        board_shell.run("ping -c 1 '{}'".format(server))

    @pytest.mark.parametrize("server", ["nic.cz", "turris.cz", "google.com"])
    def test_dns(self, board_shell, server):
        """Try to resolve verious domain names.
        """
        board_shell.run("nslookup '{}'".format(server))
# TODO more excessive DNS testing
