"""Check if nsfarm-internet really has the Internet access.
"""
import pytest
from nsfarm.lxd import Container
from nsfarm.cli import Shell
from .test_image import BASE_IMG


@pytest.fixture(scope="module")
def container(lxd_connection):
    """Base container to be used for testing.
    """
    with Container(lxd_connection, BASE_IMG, internet=True) as cont:
        shell = Shell(cont.pexpect())
        shell.run("wait4network")
        yield shell


@pytest.mark.parametrize("server", [
    "217.31.205.50",  # nic.cz
    "nic.cz",
    "turris.cz",
    "repo.turris.cz",
    "cloudflare.com",
])
def test_ping(container, server):
    """Simple ping to various IP addresses.
    """
    container.run(f"ping -c 1 '{server}'")
