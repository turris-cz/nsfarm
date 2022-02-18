"""Various OpenWrt specific setup utilities.

These are basically utilities that are specific for OpenWrt distribution.
"""
import re

from .. import cli, toolbox
from ._setup import Setup as _Setup


class OpkgInstall(_Setup):
    """Install package using OPKG.

    In most cases the usage of nsfarm.setup.updater.Updater is prefered but specially on pure OpenWrt there is no
    Updater. This allow usage of Opkg instead.
    """

    def __init__(self, shell: cli.Shell, *args: str, binary: str = "opkg"):
        """Package names are expected as positional arguments. The 'binary' argument can specify some other opkg tool
        name. The primary usecase for that is on Turris OS where plain opkg (not the wrapper) is named opkg-cl.
        """
        self._sh = shell
        # Note: there is no need for quotations because package names should not contain any special characters.
        self._pkgs = " ".join(args)
        self._to_remove: list[str] = []
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


class Service(_Setup):
    """Control service state.

    This allows to start or stop service. It does not support enable or disable as we do not need to enable in general
    as we do not have support for persistent changes between reboot in NSFarm.
    """

    def __init__(self, shell: cli.Shell, service: str, running: bool = True):
        """Initialize instance for specified service.

        shell: Shell access to the board.
        service: The service name.
        running: The wanted state of the service, True if it should be running and False if not.
        """
        self._sh = shell
        self._service = service
        self._running = running
        self._was_running = running  # Just expect that it is in ideal state if no revert needed

    def prepare(self, revert_needed: bool = True):
        if revert_needed:
            self._was_running = self.running
            if self._running == self._was_running:
                return  # Nothing to do so do not attempt
        self._sh.run(f"/etc/init.d/{self._service} {'start' if self._running else 'stop'}")

    def revert(self):
        if self._was_running != self._running:
            self._sh.run(f"/etc/init.d/{self._service} {'start' if self._was_running else 'stop'}")

    @property
    def running(self) -> bool:
        """Get current state of the service."""
        return toolbox.openwrt.service_is_running(self._service, self._sh)
