"""Verify Alpine Linux specific setup utilities from nsfarm.setup.alpine.
"""
import re

import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.setup import alpine


@pytest.fixture(name="container", scope="module")
def fixture_container(lxd_client):
    """This provides Alpine Linux container instance for all tests in this module."""
    with Container(lxd_client, "base-alpine", internet=True) as container:
        yield container


@pytest.fixture(name="shell")
def fixture_shell(container):
    """The unique shell instance in Alpine Linux container for every test."""
    shell = Shell(container.pexpect())
    shell.run("wait4network")
    return shell


def test_apkinstall(shell):
    """Check that we can install simple packages and that it is removed later on."""
    packages = ("tcpdump", "zstd")

    shell.run("apk list -I")
    installed = set(line.split(" ", maxsplit=1)[0] for line in shell.output.split("\n"))

    with alpine.ApkInstall(shell, *packages) as _:
        for pkg in packages:
            shell.run(f"apk list -I | awk '$1 ~ \"^{pkg}-\" {{ print; exit 0 }} ENDFILE {{ exit 1 }}'")

    # The set of installed packages after ApkInstall revert should be same as before.
    shell.run("apk list -I")
    assert set(line.split(" ", maxsplit=1)[0] for line in shell.output.split("\n")) == installed
