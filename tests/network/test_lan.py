"""Test LAN access of Internet and software on LAN side.
"""
import time
import pytest
import nsfarm.lxd
from . import common
# pylint: disable=no-self-use


class TestInternet(common.InternetTests):
    """Test WAN with network settings configured statically.
    """

    @pytest.fixture(scope="class", autouse=True)
    def client(self, basic_isp, lan1_client):
        """With basic router config and client is client container.
        """
        yield nsfarm.cli.Shell(lan1_client.pexpect())
