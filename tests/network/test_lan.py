"""Test LAN access of Internet and software on LAN side.
"""
import pytest
import nsfarm
from . import common

# pylint: disable=no-self-use


@pytest.mark.deploy
class TestInternet(common.InternetTests):
    """Test WAN with network settings configured statically."""

    @pytest.fixture(scope="class", autouse=True)
    def client(self, board_wan, lan1_client):
        """With basic router config and client is client container."""
        shell = nsfarm.cli.Shell(lan1_client.pexpect())
        shell.run("wait4network")
        yield shell
