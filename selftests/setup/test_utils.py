"""Verify functionality of setup utilities.
"""
from crypt import crypt

import pytest

from nsfarm.cli import Shell
from nsfarm.lxd import Container
from nsfarm.setup import openwrt, utils


class Common:
    image: str

    @pytest.fixture(name="container", scope="class")
    def fixture_container(self, lxd_client):
        with Container(lxd_client, self.image, internet=True) as container:
            container.shell.run("wait4network")
            yield container

    @pytest.fixture(name="shell")
    def fixture_shell(self, container):
        return Shell(container.pexpect())

    def test_password(self, shell):
        """Check RootPassword setup."""
        password = "ILikeWhenPlansPanOut"
        shell.run("grep '^root::' /etc/shadow")
        with utils.RootPassword(shell, password) as _:
            shell.run("awk -F: '$1 == \"root\" { print $2 }' /etc/shadow")
            pswd = shell.output.strip()
            pswd_hash, pswd_salt = pswd.split("$")[1:3]
            assert pswd == crypt(password, f"${pswd_hash}${pswd_salt}")
        shell.run("grep '^root::' /etc/shadow")

    def test_random_password(self, shell):
        """Check RootPassword setup."""
        shell.run("grep '^root::' /etc/shadow")
        with utils.RootPassword(shell) as root_password:
            shell.run("awk -F: '$1 == \"root\" { print $2 }' /etc/shadow")
            pswd = shell.output.strip()
            pswd_hash, pswd_salt = pswd.split("$")[1:3]
            assert pswd == crypt(root_password.password, f"${pswd_hash}${pswd_salt}")
        shell.run("grep '^root::' /etc/shadow")

    @pytest.fixture(name="ssh_id_rsa")
    def fixture_ssh_id_rsa(self, shell):
        shell.run("ssh-keygen -f /root/.ssh/id_rsa -N ''")
        with utils.DeployFile(
            shell,
            "/root/.ssh/config",
            "Host *\n\tStrictHostKeyChecking no\n\tPasswordAuthentication no",
        ) as _:
            yield
        shell.run("rm -f /root/.ssh/id_rsa*")

    def test_sshkey(self, shell, ssh_id_rsa, destination):
        """Check if SSHKey correctly deployes the key and allows SSH access."""
        destination_ip = destination.network.addresses["internet"][0].ip
        with utils.RootPassword(destination.shell) as _:
            shell.run(f"! ssh '{destination_ip}' true")
            with utils.SSHKey(shell, destination.shell) as _:
                shell.run(f"ssh '{destination_ip}' true")
            shell.run(f"! ssh '{destination_ip}' true")


class TestOpenWrt(Common):
    """These are tests of utility setups in OpenWrt."""

    image = "openwrt"

    @pytest.fixture(scope="class", autouse=True)
    def fixture_install_packages(self, request, container):
        # Testing password
        openwrt.OpkgInstall(container.shell, "shadow-chpasswd").request(request)


class TestAlpine(Common):
    """These are tests of utilities for Alpine Linux."""

    image = "base-alpine"

    @pytest.fixture(name="unlock_root", scope="class", autouse=True)
    def fixture_unlock_root(self, container):
        container.shell.run("passwd -u root")
