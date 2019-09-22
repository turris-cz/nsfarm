"""This defines generic board and its helpers.
"""
import sys
import time
import serial
import serial.tools.miniterm
from pexpect import fdpexpect
from . import cli
from .lxd import Container

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

        self.serial = serial.Serial(self.config['serial'], 115200)
        self.reset(True)  # Hold in reset state

        self.logfile = open("./{}.log".format(target), "wb")
        self._pexpect = fdpexpect.fdspawn(self.serial, logfile=self.logfile)

    def power(self, state):
        """Set power state.
        """
        self.serial.cst = state

    def reset(self, state):
        """Set reset pin state.
        """
        self.serial.rts = state

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
            uboot.run('setenv bootargs "earlyprintk console=ttyS0,115200 rootfstype=ramfs initrd=0x03000000"')
            uboot.run('setenv ipaddr 192.168.1.142')
            uboot.run('setenv serverip 192.168.1.1')
            uboot.run('tftpboot 0x01000000 192.168.1.1:zImage')
            uboot.run('tftpboot 0x02000000 192.168.1.1:dtb')
            uboot.run('tftpboot 0x03000000 192.168.1.1:root.uimage', timeout=120)
        self._pexpect.sendline('bootz 0x01000000 0x03000000 0x02000000')
        # Wait for bootup
        self._pexpect.expect_exact(["Router Turris successfully started.", ], timeout=120)
        # Note Shell sends new line which opens terminal for it
        # TODO why this flush timeouts?
        return cli.Shell(self._pexpect, flush=False)

    @property
    def pexpect(self):
        """pexpect handle to serial TTY interface.
        """
        return self._pexpect

    def serial_miniterm(self):
        """Runs interactive miniterm on serial TTY interface.

        This can be used only if you disable capture in pytest (--capture=no).
        """
        miniterm = serial.tools.miniterm.Miniterm(self.serial)
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


class Mox(Board):
    """Turris Mox boards.
    """


class Omnia(Board):
    """Turris Omnia board.
    """


class Turris1x(Board):
    """Turris 1.0 and 1.1 boards.
    """


def get_board(config):
    """Function which instantiates correct board class depending on target_config.
    """
    boards = {
        "mox": Mox,
        "omnia": Omnia,
        "turris1x": Turris1x,
    }
    board = config.target_config["board"]
    if board not in boards:
        raise Exception("Unknown or unsupported board: {}".format(board))
    return boards[board](config.getoption("-T"), config.target_config)
