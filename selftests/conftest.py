import pytest
import pylxd


@pytest.fixture(name="lxd_client", scope="package")
def fixture_lxd_client():
    return pylxd.Client()
