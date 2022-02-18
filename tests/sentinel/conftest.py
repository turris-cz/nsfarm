import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.setup.openwrt import Service
from nsfarm.setup.updater import Pkglist

from .test_dynfw import IPSET


@pytest.fixture(scope="package", autouse=True)
def fixture_sentinel(request, board_wan, updater_branch, client_board):
    """Set that we agree with Sentinel EULA."""
    Pkglist(client_board, "datacollect").request(request)
    client_board.run("uci set sentinel.main.agreed_with_eula_version=1 && uci commit sentinel.main")
    request.addfinalizer(
        lambda: client_board.run(
            "uci delete sentinel.main.agreed_with_eula_version && uci commit sentinel.main && sentinel-reload"
        )
    )
    client_board.run("sentinel-reload")


@pytest.fixture(scope="package", name="attacker_container")
def fixture_attacker_container(lxd_client, device_map):
    """Container serving as an attacker from the Internet. In this case it is in the same network as ISP but that is
    intentional as this way we won't poison data that much even if we send them to Sentinel network.
    """
    with Container(lxd_client, "attacker", device_map) as container:
        container.shell.run("wait4boot")
        yield container


@pytest.fixture(scope="package", name="attacker")
def fixture_attacker(attacker_container):
    """Shell access to attacker container."""
    return Shell(attacker_container.pexpect())


@pytest.fixture(scope="function", name="dynfw_block_attacker")
def fixture_dynfw_block_attacker(client_board):
    """Add our attacker container to ipset managed by dynfw. This way we can test firewall settings for dynfw."""
    # Note: We disable dynfw client so we do not interfere with it.
    with Service(client_board, "sentinel-dynfw-client", running=False):
        client_board.run(f"ipset add '{IPSET}' 172.16.42.42")
        yield
        client_board.run(f"ipset del '{IPSET}' 172.16.42.42 || true")
