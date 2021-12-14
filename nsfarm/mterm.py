"""Micro terminal to interface on top of generic socket and stdout/stderr.
"""
import fcntl
import io
import logging
import os
import select
import sys
import termios
import warnings

EXIT_CHAR = b"\x1d"


def _setup_stdin():
    # Set terminal to raw mode. This is technically an implementation of cfmakeraw function.
    new_tio = termios.tcgetattr(sys.stdin)
    new_tio[0] &= ~(
        termios.IGNBRK
        | termios.BRKINT
        | termios.PARMRK
        | termios.ISTRIP
        | termios.INLCR
        | termios.IGNCR
        | termios.ICRNL
        | termios.IXON
    )
    new_tio[1] &= ~termios.OPOST
    new_tio[2] &= ~(termios.CSIZE | termios.PARENB)
    new_tio[2] |= termios.CS8
    new_tio[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG | termios.IEXTEN)
    termios.tcsetattr(sys.stdin, termios.TCSANOW, new_tio)


def mterm(fileno: int):
    """Run micro terminal."""
    if not sys.stdin.isatty():
        warnings.warn("Microterm works only if stdin is directly the terminal.", RuntimeWarning)
        return
    prev_log_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.CRITICAL)
    orig_tio = termios.tcgetattr(sys.stdin)
    orig_filestatus = fcntl.fcntl(fileno, fcntl.F_GETFL)
    print("--- Microterm (use ^] to exit) ---", file=sys.stderr)
    try:
        _setup_stdin()
        fcntl.fcntl(fileno, fcntl.F_SETFL, orig_filestatus | os.O_NONBLOCK)
        output = {
            sys.stdin.fileno(): fileno,
            fileno: sys.stdout.fileno(),
        }
        poll = select.poll()
        poll.register(sys.stdin.fileno(), select.POLLIN)
        poll.register(fileno, select.POLLIN)
        terminate = False
        while not terminate:
            for poll_event in poll.poll():
                poll_fileno, _ = poll_event
                data = os.read(poll_fileno, io.DEFAULT_BUFFER_SIZE)
                if poll_fileno == sys.stdin.fileno() and EXIT_CHAR in data:
                    data = data.partition(EXIT_CHAR)[0]
                    terminate = True
                os.write(output[poll_fileno], data)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSANOW, orig_tio)
        fcntl.fcntl(fileno, fcntl.F_SETFL, orig_filestatus)
        logging.getLogger().setLevel(prev_log_level)
        print("\n--- Microterm exit ---", file=sys.stderr)
