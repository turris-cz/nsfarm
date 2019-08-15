"""This defines generic board and its helpers.
"""
import os
import serial
import serial.tools.miniterm
from pexpect import fdpexpect
from . import cli

MINITERM_DEFAULT_EXIT = '\x1d'  # Ctrl+]
MINITERM_DEFAULT_MENU = '\x14'  # Ctrl+T
MINITERM_ENCODING = sys.getdefaultencoding()


class Board():
    def __init__(self, target, target_config):
        """Initialize board handler.
        serial: path to serial tty
        """
        self.config = target_config

        self.serial = serial.Serial(self.config['serial'], 115200)
        self.reset(True)  # Hold in reset state

        self.logfile = open("./{}.log".format(target), "wb")
        self.pexpect = fdpexpect.fdspawn(self.serial, logfile=self.logfile)

    def uboot(self):
        """Ensures that board is booted to u-boot and ready to accept u-boot
        commands.

        Returns instance of cli.Uboot
        """
        # TODO reset pin and so on..
        return cli.Uboot(self.pexpect)

    def system(self, medkit):
        """Ensures that board runs system from given medkit and that shell is
        accessible and ready to accept commands.
        """

    def reset(self, state):
        """Set reset pin state.
        """
        self.serial.rts = state

    def serial_pexpect(self):
        """Returns pexpect handle to serial TTY interface.
        """
        return self.pexpect

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Omnia(Board):
    """Turris Omnia board.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Turris1x(Board):
    """Turris 1.0 and 1.1 boards.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def get_board(config):
    """Function which instantiates correct board class depending on
    target_config.
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
