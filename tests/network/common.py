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
        "217.31.205.50",  # nic.cz
        "nic.cz",
        "turris.cz",
        "google.com"
    ])
    def test_ping(self, client_board, server):
        """Ping various IPv4 servers.

        We send only one ICMP packet to not flood and to be quickly done with it (the success takes less than second)
        """
        client_board.run("ping -c 1 '{}'".format(server))

    @pytest.mark.parametrize("server", [
        "nic.cz",
        "turris.cz",
        "google.com"
    ])
    def test_dns(self, client_board, server):
        """Try to resolve verious domain names.
        """
        client_board.run("nslookup '{}'".format(server))

    # TODO more excessive DNS testing
