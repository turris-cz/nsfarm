"""Various OpenWrt specific setup utilities.
These are basically utilities that are specific for OpenWrt distribution.
"""
import re

from .. import cli
from ._setup import Setup as _Setup


class OpkgInstall(_Setup):
    """In most cases the usage of nsfarm.setup.updater.Updater is prefered but specially on pure OpenWrt there is no
    Updater. This allow usage of Opkg instead.
    """

    def __init__(self, shell: cli.Shell, *args: str, binary: str = "opkg"):
        """Package names are expected as positional arguments. The 'binary' argument can specify some other opkg tool
        name. The primary usecase for that is on Turris OS where plain opkg (not the wrapper) is named opkg-cl.
        """
        self._sh = shell
        # Note: there is no need for quotations because package names should not contain any special characters.
        self._pkgs = " ".join(args)
        self._to_remove = []
        self._opkg = binary

    def prepare(self, revert_needed: bool = True):
        self._sh.run(f'[ -n "$(ls /tmp/opkg-lists 2>/dev/null)" ] || {self._opkg} update')
        self._sh.run(f"{self._opkg} install {self._pkgs}")
        if not revert_needed:
            return
        # Note: We are using configuration report here because opkg spits them out in dependency order thus we can
        # remove all installed packages in the reverse order to not raise error. The line consist of word "Configuring"
        # with package name and ends with dot. We strip it here to package name only by removing first word and tailing
        # character.
        match_pkg = re.compile(r"Configuring (.+)\.")
        for line in self._sh.output.split("\n"):
            match = match_pkg.match(line)
            if match:
                self._to_remove.insert(0, match.group(1))

    def revert(self):
        pkgs = " ".join(self._to_remove)
        self._sh.run(f"{self._opkg} remove {pkgs}")
