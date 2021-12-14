import pathlib

import pytest


@pytest.mark.parametrize(
    "device",
    [
        "/dev/ppp",
    ],
)
def test_local_device(device):
    """Check that we have local device required for testing."""
    assert pathlib.Path(device).exists()
