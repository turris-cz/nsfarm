import pytest
from nsfarm import lxd


@pytest.fixture(name="lxd_connection", scope="package")
def fixture_lxd_connection():
    return lxd.LXDConnection()
