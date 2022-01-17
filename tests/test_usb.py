"""These are very simple tests to check that USB is working."""
import pytest


def pytest_generate_tests(metafunc):
    if "bus_index" not in metafunc.fixturenames:
        return
    buses = {
        "omnia": 5,
        "mox": 3,
    }
    if metafunc.config.target_config.board in buses:
        metafunc.parametrize("bus_index", list(range(1, buses[metafunc.config.target_config.board] + 1)))
    else:
        metafunc.parametrize("bus_index", [pytest.param("no-usb-bus", marks=pytest.mark.skip)])


@pytest.mark.deploy
def test_root_hub(board_access, bus_index):
    """Check that USB root HUBs are visible in UBS listing.

    This is minimal of what has to be visible even if there are no devices connected.
    """
    shell = board_access()
    shell.run(f"lsusb -s '{bus_index}:1'")
    assert shell.output
