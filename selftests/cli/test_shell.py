"""Shell class tests.
"""
import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container


class Common:
    """Common tests implementation for Shell."""

    @pytest.fixture(autouse=True)
    def shell(self, container):
        return Shell(container.pexpect())

    def test_true(self, shell):
        """Simple command that has no effect just to test full process match."""
        shell.run("true")

    def test_false(self, shell):
        """Simple command that has no effect but fails with known exit code."""
        assert shell.run("false", None) == 1

    @pytest.fixture
    def test_file(self, shell):
        """This provides test file path that is removed after test finishes."""
        path = "/tmp/test-file"
        yield path
        shell.run(f"rm -f '{path}'")

    def test_txt(self, request, shell, test_file):
        """Check for simple use of txt_write and txt_read."""
        txt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et \
            dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex \
            ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu \
            fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt \
            mollit anim id est laborum."
        shell.txt_write(test_file, txt)
        assert txt == shell.txt_read(test_file)

    def test_txt_multiline(self, request, shell, test_file):
        """Check for multiline use of txt_write and txt_read."""
        txt = """Lorem ipsum dolor sit amet,
        consectetur adipiscing elit,
        sed do eiusmod tempor incididunt ut labore et
        dolore magna aliqua. Ut enim ad minim veniam,
        quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
        commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat \
        nulla pariatur. Excepteur sint occaecat cupidatat non proident,
        sunt in culpa qui officia deserunt mollit anim id est laborum."""
        shell.txt_write(test_file, txt)
        assert txt == shell.txt_read(test_file)

    def test_txt_append(self, request, shell, test_file):
        """Check if txt_read append option works as expected."""
        txt1 = "First line"
        txt2 = "Second line"
        shell.txt_write(test_file, txt1)
        shell.txt_write(test_file, txt2, append=True)
        assert f"{txt1}\n{txt2}" == shell.txt_read(test_file)

    def test_bin(self, request, shell, test_file):
        """Check if txt_read append option works as expected."""
        data = b"\x01\x02\x03\x04\x05"
        shell.bin_write(test_file, data)
        assert data == shell.bin_read(test_file)


class TestOpenWrt(Common):
    """These are tests in OpenWrt (ash) shell."""

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_client):
        with Container(lxd_client, "openwrt") as container:
            yield container


class TestAlpine(Common):
    """These are tests in Alpine Linux (ash) shell."""

    @pytest.fixture(scope="class", autouse=True)
    def container(self, lxd_client):
        with Container(lxd_client, "base-alpine") as container:
            yield container
