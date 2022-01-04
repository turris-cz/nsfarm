"""These tests just check that Sentinel components are running after installation.
"""
import pytest

from nsfarm.toolbox.openwrt import service_is_running

sentinel_services = [
    "sentinel-dynfw-client",
    "sentinel-proxy",
    "sentinel-minipot",
    # TODO add sentinel-fwlogs replacing sentinel-nikola once deployed
]


@pytest.mark.deploy
@pytest.mark.parametrize("service", sentinel_services)
def test_service_running(client_board, service):
    """Check if expected processes we need for Sentinel are running and thus all should be correctly configured."""
    assert service_is_running(service, client_board)


@pytest.mark.deploy
@pytest.mark.parametrize("service", sentinel_services)
def test_service_enabled(client_board, service):
    """Check if expected processes we need for Sentinel are running and thus all should be correctly configured."""
    client_board.run(f"/etc/init.d/{service} enabled")
