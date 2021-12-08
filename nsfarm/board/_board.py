"""This defines generic board and its helpers.
"""
import abc
import logging
import time

import serial
import serial.tools.miniterm
from pexpect import fdpexpect

from .. import cli
from ..lxd import Container
from ..target.target import Target


class Board(abc.ABC):
    """General abstract class defining handle for board."""

    def __init__(self, target_config: Target):
        self.config = target_config
        # Open serial console to board
        self._serial = serial.Serial(self.config.serial, 115200)
        self._fdlogging = cli.FDLogging(self._serial.fileno(), logging.getLogger(__package__))
        self._pexpect = fdpexpect.fdspawn(self._fdlogging.socket)
        # Set board to some known state
        self.reset(True)  # Hold in reset state
        # Set default baord constants for testing
        self.min_eth_throughput = 400  # Mbps

    @property
    def pexpect(self):
        """pexpect handle to serial TTY interface."""
        return self._pexpect

    def set_serial_flush(self, flush: bool):
        """Enables/Disables serial data flush.
        This disables data propagation in logging and flushes pexpect on disable. The effect is that output is only
        logged without propagation to pexpect.
        This is required as at some point we just use serial console for logs without reading it. In such case it is
        just matter of time logger gets stuck as pipe toward pexpect gets filled. This prevents this from happening.
        """
        self._fdlogging.set_propagation(not flush)
        if flush:
            cli.pexpect_flush(self._pexpect)

    def power(self, state):
        """Set power state."""
        self._serial.cst = state

    def reset(self, state):
        """Set reset pin state."""
        self._serial.rts = state

    def uboot(self):
        """Ensures that board is booted to u-boot and ready to accept u-boot commands.

        Returns instance of cli.Uboot
        """
        # Restart board so we are sure that we are running U-Boot
        self.reset(True)
        time.sleep(0.001)
        self.reset(False)
        # Now wait for U-Boot hint to get CLI
        self._pexpect.expect_exact("Hit any key to stop autoboot: ")
        self._pexpect.sendline("")
        return cli.Uboot(self._pexpect)

    def bootup(self, lxd_client, os_branch: str) -> cli.Shell:
        """Boot board using TFTP boot. This ensures that board is booted up and ready to accept commands.

        os_branch: Turris OS branch to download medkit from.

        Returns instance of cli.Shell
        """
        # First get U-Boot prompt
        uboot = self.uboot()
        # Now load image from TFTP
        with Container(lxd_client, "boot", self.config.device_map()) as cont:
            ccli = cli.Shell(cont.pexpect())
            ccli.run(f"prepare_turris_image '{self.config.board}' '{os_branch}'", timeout=120)
            uboot.run("setenv ipaddr 192.168.1.142")
            uboot.run("setenv serverip 192.168.1.1")
            self._board_bootup(uboot)
        # Wait for bootup
        self._pexpect.expect_exact("Router Turris successfully started.", timeout=240)
        self._pexpect.sendline("")
        shell = cli.Shell(self._pexpect)
        shell.run("sysctl -w kernel.printk='0 4 1 7'")  # disable kernel print to not confuse console flow
        return shell

    @abc.abstractmethod
    def _board_bootup(self, uboot):
        """Board specific bootup routine.

        It has to implement TFTP uboot routines.
        """

    @property
    @abc.abstractmethod
    def wan(self):
        """Network interface name for WAN interface in router"""

    @property
    @abc.abstractmethod
    def lan1(self):
        """Network interface name for LAN1 interface in router
        Note that this not matches lan1 port on router but rather is primary lan port.
        """

    @property
    @abc.abstractmethod
    def lan2(self):
        """Network interface name for LAN2 interface in router
        Note that this not matches lan2 port on router but rather is secondary test port (such as different switch).
        """

    @property
    @abc.abstractmethod
    def lan3(self):
        """Network interface name for LAN3 interface in router
        Note that this not matches lan3 port on router but rather is tercial test port (such as different switch).
        """
