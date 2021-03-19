import pytest


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
