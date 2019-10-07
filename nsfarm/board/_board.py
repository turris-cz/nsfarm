"""This defines generic board and its helpers.
"""
import sys
import time
import logging
import serial
import serial.tools.miniterm
from pexpect import fdpexpect
from .. import cli
from ..lxd import Container

MINITERM_DEFAULT_EXIT = '\x1d'  # Ctrl+]
MINITERM_DEFAULT_MENU = '\x14'  # Ctrl+T
MINITERM_ENCODING = sys.getdefaultencoding()


class Board:
    """General abstract class defining handle for board.
    """

    def __init__(self, target, target_config):
        """Initialize board handler.
        serial: path to serial tty
        """
        self.config = target_config
        # Open serial console to board
        self._serial = serial.Serial(self.config['serial'], 115200)
        self._pexpect = fdpexpect.fdspawn(self._serial)
        self._pexpect.logfile_read = cli.PexpectLogging(logging.getLogger('{}[{}]'.format(__package__, target)))
        # Set board to some known state
        self.reset(True)  # Hold in reset state

    @property
    def pexpect(self):
        """pexpect handle to serial TTY interface.
        """
        return self._pexpect

    def power(self, state):
        """Set power state.
        """
        self._serial.cst = state

    def reset(self, state):
        """Set reset pin state.
        """
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
        self._pexpect.expect_exact(["Hit any key to stop autoboot: ", ])
        self._pexpect.sendline("")
        return cli.Uboot(self._pexpect)

    def bootup(self, device_wan):
        """Boot board using TFTP boot. This ensures that board is booted up and ready to accept commands.

        device_wan: Wan device to board. This is instance of nsfarm.lxd.NetInterface.

        Returns instance of cli.Shell
        """
        # First get U-Boot prompt
        uboot = self.uboot()
        # Now load image from TFTP
        with Container("boot", devices=[device_wan, ]) as cont:
            ccli = cli.Shell(cont.pexpect())
            ccli.run("prepare_turris_image")
            uboot.run('setenv ipaddr 192.168.1.142')
            uboot.run('setenv serverip 192.168.1.1')
            self._board_bootup(uboot)
        # Wait for bootup
        self._pexpect.expect_exact(["Router Turris successfully started.", ], timeout=120)
        # Note Shell sends new line which opens terminal for it
        shell = cli.Shell(self._pexpect, flush=False)  # TODO why this flush timeouts?
        shell.run("sysctl -w kernel.printk='0 4 1 7'")  # disable kernel print to not confuse console flow
        return shell

    def _board_bootup(self, uboot):
        """Board specific bootup routine.

        It has to implement TFTP uboot routines.
        """
        raise NotImplementedError

    def serial_miniterm(self):
        """Runs interactive miniterm on serial TTY interface.

        This can be used only if you disable capture in pytest (--capture=no).
        """
        miniterm = serial.tools.miniterm.Miniterm(self._serial, echo=False)
        miniterm.exit_character = MINITERM_DEFAULT_EXIT
        miniterm.menu_character = MINITERM_DEFAULT_MENU
        miniterm.set_rx_encoding(MINITERM_ENCODING)
        miniterm.set_tx_encoding(MINITERM_ENCODING)

        sys.stderr.write('\n')
        sys.stderr.write('--- Miniterm on {p.name} ---\n'.format(p=miniterm.serial))
        sys.stderr.write('--- Quit: {0} | Menu: {1} | Help: {1} followed by {2} ---\n'.format(
            serial.tools.miniterm.key_description(miniterm.exit_character),
            serial.tools.miniterm.key_description(miniterm.menu_character),
            serial.tools.miniterm.key_description('\x08')))

        miniterm.start()
        miniterm.join()

        sys.stderr.write("\n--- Miniterm exit ---\n")

    @property
    def wan(self):
        """Network interface name for WAN interface in router
        """
        raise NotImplementedError

    @property
    def lan1(self):
        """Network interface name for LAN1 interface in router
        """
        raise NotImplementedError

    @property
    def lan2(self):
        """Network interface name for LAN2 interface in router
        """
        raise NotImplementedError

    @property
    def lan3(self):
        """Network interface name for LAN3 interface in router
        """
        raise NotImplementedError
