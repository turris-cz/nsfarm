"""Shell class tests.
"""
import pytest
from nsfarm.cli import Shell
from nsfarm.lxd import Container
# pylint: disable=no-self-use


class Common:
    """Common tests implementation for Shell.
    """

    @pytest.fixture(scope="function", autouse=True)
    def shell(self, container):
        return Shell(container.pexpect())

    def test_true(self, shell):
        """Simple command that has no effect just to test full process match.
        """
        shell.run("true")

    def test_false(self, shell):
        """Simple command that has no effect but fails with known exit code.
        """
        assert shell.run("false", None) == 1


class TestOpenWrt(Common):
    """These are tests in OpenWrt (ash) shell.
    """

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_connection):
        with Container(lxd_connection, "openwrt") as container:
            yield container


class TestAlpine(Common):
    """These are tests in Alpine Linux (ash) shell.
    """

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_connection):
        with Container(lxd_connection, "base-alpine") as container:
            yield container
