"""Tests for sentinel-minipot.
"""
import abc

import pytest

from nsfarm.cli import CTRL_D

# pylint: disable=unused-argument


class GenericMinipot(abc.ABC):
    """Generic test definition for minipot."""

    @abc.abstractstaticmethod
    def access(attacker_container, attacker, board_wan):
        """Try if we can access service."""

    def test_simple_connect(self, attacker_container, attacker, board_wan):
        """Checks if we can access telnet."""
        self.access(attacker_container, attacker, board_wan)

    def test_blocked_connect(self, attacker_container, attacker, board_wan, dynfw_block_attacker):
        """Checks if we can access telnet even if dynfw blocks attacker.
        This checks if dynfw bypass works and thus we can collect attackers even if they are blocked.
        """
        self.access(attacker_container, attacker, board_wan)


class TestTelnet(GenericMinipot):
    """Telnet minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan):
        telnet = attacker_container.pexpect(("telnet", board_wan))
        telnet.expect_exact("Username: ")
        telnet.send(CTRL_D)


class TestFTP(GenericMinipot):
    """FTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan):
        attacker.run(f"ncftp -u nsfarm -p nsfarm '{board_wan}' </dev/null")
        assert (
            f"Could not open host {board_wan}: username and/or password was not accepted for login." in attacker.output
        )


class TestHTTP(GenericMinipot):
    """HTTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan):
        attacker.run(f"wget 'http://{board_wan}'", exit_code=lambda ec: ec == 1)
        assert "wget: server returned error: HTTP/1.1 401 Unauthorized" in attacker.output


class TestSMTP(GenericMinipot):
    """SMTP minipot access tests."""

    @staticmethod
    def access(attacker_container, attacker, board_wan):
        telnet = attacker_container.pexpect(("telnet", board_wan, "587"))
        telnet.expect(r"220 .* ESMTP Postfix \(Debian\/GNU\)")
        telnet.send(CTRL_D)
