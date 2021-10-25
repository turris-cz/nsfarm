"""Generic utilities that work on all Unix-like platforms as they are based on pure shell operations.
"""
import random
import string
import typing

from .. import cli
from ._setup import Setup as _Setup


class RootPassword(_Setup):
    """Sets given or random password as the one for root."""

    def __init__(self, shell: cli.Shell, password: typing.Optional[str] = None):
        self._sh = shell
        self.password = password if password else "".join(random.choice(string.ascii_lowercase) for i in range(16))

    def prepare(self, revert_needed: bool = True):
        # TODO what about previous password
        self._sh.run(f"echo 'root:{self.password}' | chpasswd")

    def revert(self):
        self._sh.run("passwd -d root")
