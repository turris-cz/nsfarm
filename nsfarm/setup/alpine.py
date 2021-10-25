"""Various Alpine Linux specific setup utilities.
"""
from .. import cli
from ._setup import Setup as _Setup


class ApkInstall(_Setup):
    """Package installation on Alpine Linux."""

    def __init__(self, shell: cli.Shell, *args: str):
        """Package names are expected as positional arguments."""
        self._sh = shell
        # Note: there is no need for quotations because package names should not contain any special characters.
        self._pkgs = " ".join(args)

    def prepare(self, revert_needed: bool = True):
        self._sh.run(f"apk --no-progress add {self._pkgs}")

    def revert(self):
        self._sh.run(f"apk --no-progress del {self._pkgs}")
