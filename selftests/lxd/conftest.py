import pytest
from nsfarm import lxd


@pytest.fixture(name="connection", scope="package")
def fixture_connection():
    return lxd.LXDConnection()
