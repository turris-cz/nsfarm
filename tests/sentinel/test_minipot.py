"""Tests for sentinel-minipot.
"""
import abc

import pytest

from nsfarm.cli import CTRL_D

# pylint: disable=unused-argument


class GenericMinipot(abc.ABC):
    """Generic test definition for minipot."""

    @staticmethod
    @abc.abstractmethod
    def access(attacker_container, attacker, board_wan_ip):
        """Try if we can access service."""

    def test_simple_connect(self, attacker_container, attacker, board_wan):
        """Checks if we can access telnet."""
        self.access(attacker_container, attacker, board_wan.network.ip)

    def test_blocked_connect(self, attacker_container, attacker, board_wan, dynfw_block_attacker):
        """Checks if we can access telnet even if dynfw blocks attacker.
        This checks if dynfw bypass works and thus we can collect attackers even if they are blocked.
        """
        self.access(attacker_container, attacker, board_wan.network.ip)


class TestTelnet(GenericMinipot):
    """Telnet minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan_ip):
        telnet = attacker_container.pexpect(("telnet", str(board_wan_ip)))
        telnet.expect_exact("Username: ")
        telnet.send(CTRL_D)


class TestFTP(GenericMinipot):
    """FTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan_ip):
        attacker.run(f"ncftp -u nsfarm -p nsfarm '{board_wan_ip}' </dev/null")
        assert (
            f"Could not open host {board_wan_ip}: username and/or password was not accepted for login."
            in attacker.output
        )


class TestHTTP(GenericMinipot):
    """HTTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan_ip):
        assert attacker.run(f"wget 'http://{board_wan_ip}'", check=False) == 1
        assert "wget: server returned error: HTTP/1.1 401 Unauthorized" in attacker.output


class TestSMTP(GenericMinipot):
    """SMTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan_ip):
        telnet = attacker_container.pexpect(("telnet", str(board_wan_ip), "587"))
        telnet.expect(r"220 .* ESMTP Postfix \(Debian\/GNU\)")
        telnet.send(CTRL_D)
