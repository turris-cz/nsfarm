import pytest
from nsfarm.lxd import Container
from nsfarm.cli import Shell
from .test_dynfw import IPSET


@pytest.fixture(scope="module", autouse=True)
def fixture_sentinel(request, board_wan, updater_branch,  client_board):
    """Set that we agree with Sentinel EULA.
    """
    client_board.run("uci add_list pkglists.pkglists.pkglist=datacollect && uci commit pkglists.pkglists")
    request.addfinalizer(lambda: client_board.run(
        "uci del_list pkglists.pkglists.pkglist=datacollect && uci commit pkglists.pkglists"))
    client_board.run("pkgupdate --batch || true", timeout=120)  # TODO updater fails because of schnapps hooks fail

    client_board.run("uci set sentinel.main.agreed_with_eula_version=1 && uci commit sentinel.main")
    request.addfinalizer(lambda: client_board.run(
        "uci delete sentinel.main.agreed_with_eula_version && uci commit sentinel.main && sentinel-reload"))
    client_board.run("sentinel-reload")


@pytest.fixture(scope="module", name="attacker_container")
def fixture_attacker_container(lxd_client, device_map):
    """Container serving as an attacker from the Internet. In this case it is in the same network as ISP but that is
    intentional as this way we won't poison data that much even if we send them to Sentinel network.
    """
    with Container(lxd_client, 'attacker', device_map) as container:
        container.shell.run('wait4boot')
        yield container


@pytest.fixture(scope="module", name="attacker")
def fixture_attacker(attacker_container):
    """Shell access to attacker container.
    """
    return Shell(attacker_container.pexpect())


@pytest.fixture(scope="function", name="dynfw_block_attacker")
def fixture_dynfw_block_attacker(client_board):
    """Add our attacker container to ipset managed by dynfw. This way we can test firewall settings for dynfw.
    """
    client_board.run(f"ipset add '{IPSET}' 172.16.42.42")
    yield
    client_board.run(f"ipset del '{IPSET}' 172.16.42.42")
