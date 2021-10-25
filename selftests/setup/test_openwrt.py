"""Verify OpenWrt specific setup utilities from nsfarm.setup.openwrt.
"""
import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.setup import openwrt


@pytest.fixture(name="container", scope="module")
def fixture_container(lxd_client):
    """This provides OpenWrt container instance for all tests in this module."""
    with Container(lxd_client, "openwrt", internet=True) as container:
        yield container


@pytest.fixture(name="shell")
def fixture_shell(container):
    """The unique shell instance in OpenWrt container for every test."""
    shell = Shell(container.pexpect())
    shell.run("wait4network")
    return shell


def test_opkginstall(shell):
    """Check that we can install simple packages and that it is removed later on."""
    packages = ("sqlite3-cli", "zstd")

    shell.run("opkg list-installed")
    installed = set(line.split(" ", maxsplit=1)[0] for line in shell.output.split("\n"))

    assert set(packages) not in installed

    with openwrt.OpkgInstall(shell, *packages) as _:
        for pkg in packages:
            shell.run(f"opkg list-installed | awk '$1 == \"{pkg}\" {{ print; exit 0 }} ENDFILE {{ exit 1 }}'")

    # The set of installed packages after OpkgInstall revert should be same as before.
    shell.run("opkg list-installed")
    assert set(line.split(" ", maxsplit=1)[0] for line in shell.output.split("\n")) == installed
