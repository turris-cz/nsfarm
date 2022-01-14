"""These are very simple tests to check that PCI is working."""
import pytest


def pytest_generate_tests(metafunc):
    if "bus_index" not in metafunc.fixturenames:
        return
    buses = {
        "omnia": range(1, 4),
        "mox": [0],
    }
    if metafunc.config.target_config.board in buses:
        metafunc.parametrize("bus_index", list(buses[metafunc.config.target_config.board]))
    else:
        metafunc.parametrize("bus_index", [pytest.param("no-usb-bus", marks=pytest.mark.skip)])


@pytest.mark.deploy
def test_omnia_pci_bridge(board_access, bus_index):
    """Check that SoC is visible in listed PCI devices.

    This is minimal of what has to be visible even if there are no devices connected.
    """
    shell = board_access()
    shell.run(f"lspci -s '00:{bus_index}.0'")
    assert shell.output
