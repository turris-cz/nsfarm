import pytest
from nsfarm import lxd


@pytest.mark.parametrize("profile", [
    lxd.LXDConnection.ROOT_PROFILE,
    lxd.LXDConnection.INTERNET_PROFILE,
])
def test_profiles_exists(lxd_connection, profile):
    """Check that all profiles we need are configured in LXD.
    """
    assert lxd_connection.local.profiles.exists(profile)


def test_profile_root(lxd_connection):
    """Minimal sanity check of root profile.
    """
    profile = lxd_connection.local.profiles.get(lxd.LXDConnection.ROOT_PROFILE)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "disk")


def test_profile_internet(lxd_connection):
    """Minimal sanity check of internet profile.
    """
    profile = lxd_connection.local.profiles.get(lxd.LXDConnection.INTERNET_PROFILE)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "nic" and dev["name"] == "internet")
