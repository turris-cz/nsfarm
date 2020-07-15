import pytest
from nsfarm import lxd


@pytest.fixture(name="connection", scope="module")
def fixture_connection():
    return lxd.LXDConnection()


@pytest.mark.parametrize("profile", [
    lxd.LXDConnection.ROOT_PROFILE,
    lxd.LXDConnection.INTERNET_PROFILE,
])
def test_profiles_exists(connection, profile):
    """Check that all profiles we need are configured in LXD.
    """
    assert connection.local.profiles.exists(profile)


def test_profile_root(connection):
    """Minimal sanity check of root profile.
    """
    profile = connection.local.profiles.get(lxd.LXDConnection.ROOT_PROFILE)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "disk")


def test_profile_internet(connection):
    """Minimal sanity check of internet profile.
    """
    profile = connection.local.profiles.get(lxd.LXDConnection.INTERNET_PROFILE)
    assert any(dev for dev in profile.devices.values() if dev["type"] == "nic" and dev["name"] == "internet")
