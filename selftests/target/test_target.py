from pathlib import Path
import pytest


def test_valid(target):
    """Simply check if we consider this target valid using verify method."""
    assert target.check()


@pytest.mark.parametrize(
    "interface",
    [
        "wan",
        "lan1",
        "lan2",
    ],
)
def test_network_up(target, interface):
    """Interfaces have to be up for macvlan to work. LXD at the moment won't bring them up automatically."""
    if not target.is_configured(interface):
        pytest.skip(f"Interface '{interface}' is not configured for this target.")
    pth = Path("/sys/class/net")
    with open(pth / target.device_map()[f"net:{interface}"] / "flags", "r") as file:
        assert int(file.readline(), base=16) & 0x1
