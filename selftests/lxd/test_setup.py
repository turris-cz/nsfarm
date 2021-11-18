import pytest
import pylxd
from nsfarm import lxd


@pytest.mark.parametrize(
    "profile",
    [
        lxd.PROFILE_ROOT,
        lxd.PROFILE_INTERNET,
    ],
)
def test_profiles_exists(lxd_client, profile):
    """Check that all profiles we need are configured in LXD."""
    assert lxd_client.profiles.exists(profile)


def test_profile_root(lxd_client):
    """Minimal sanity check of root profile."""
    profile = lxd_client.profiles.get(lxd.PROFILE_ROOT)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "disk")


def test_profile_internet(lxd_client):
    """Minimal sanity check of internet profile."""
    profile = lxd_client.profiles.get(lxd.PROFILE_INTERNET)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "nic" and dev["name"] == "internet")
