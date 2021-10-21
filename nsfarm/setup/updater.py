"""Setup utilities to configure and run updater.
"""
import collections.abc
import random
import string
import typing
import warnings

from .. import cli
from ._setup import Setup as _Setup

PUB_TEST_KEY = """untrusted comment: Turris OS devel key
RWS0FA1Nun7JDt0L8SjRsDRJGDvUCdDdfs21feiW+qpGHNMhVZ930hky
"""


def pkgupdate(shell: cli.Shell, fatal: bool = False) -> None:
    """This runs pkgupdate and waits for termination.

    fatal: The updater commonly reports failure because some specific package failed to execute correctly. We are not
        commonly interested in that so we only report that as warning in default. Making that fatal raises exception
        instead.
    """

    def exit_code_handle(exit_code):
        # TODO we should investigate output to detect updater failures over package failures
        if exit_code != 0:
            if fatal:
                raise Exception(f"pkgupdate exited with exit code: {exit_code}")
            warnings.warn(f"pkgupdate exited with exit code: {exit_code}")

    # Note: We are running from initram so we do not want to do reboot as it would wipe our state.
    shell.run("pkgupdate --batch --no-immediate-reboot", exit_code=exit_code_handle, timeout=240)
    # TODO possibly add option to also reset changelog file (/usr/share/updater/changelog) after execution


class UpdaterBranch(_Setup):
    """Configure updater for given branch."""

    def __init__(self, shell: cli.Shell, target_branch: str):
        self._sh = shell
        self.target_branch = target_branch

    def prepare(self, revert_needed: bool = True):
        if self.target_branch == "hbk":
            # HBK needs special tweak as these medkits do not contain test key but repository is signed with it.
            # WARNING we do not remove this file
            self._sh.txt_write("/etc/updater/keys/test.pub", PUB_TEST_KEY)
        self._sh.run(f"uci set updater.turris.branch='{self.target_branch}' && uci commit updater.turris.branch")

    def revert(self):
        # TODO use UCI setup here and allow nesting as blind removal is not correct
        self._sh.run("uci del updater.turris.branch && uci commit updater.turris.branch")


class Updater(_Setup):
    """Setup tool to install packages and in general configure and run the updater.

    To apply changes you have to call execute method.
    """

    def __init__(self, shell: cli.Shell, name: typing.Optional[str] = None):
        self._sh = shell
        self._name = name if name is not None else "".join(random.choices(string.ascii_lowercase, k=12))
        self._fpath = f"/etc/updater/conf.d/{self._name}.lua"

    def prepare(self, revert_needed: bool = True):
        pass

    def revert(self):
        self._sh.run(f"rm -f '{self._fpath}'")
        pkgupdate(self._sh)

    def execute(self) -> None:
        """Execute pkgupdate and wait for completion."""
        pkgupdate(self._sh)

    @classmethod
    def _2lua(cls, value: typing.Union[None, str, int, bool, dict]):
        """Converts limited Python types to Lua representation."""
        if value is None:
            return "nil"
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, int):
            return str(int)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, dict):
            fields = ", ".join(f"[{cls._2lua(key)}]={cls._2lua(value)}" for key, value in value.items())
            return f"{{ {fields} }}"
        raise Exception(f"Unsupported type to conver: {type(value)}")

    def install(self, *args: str, extra: typing.Optional[dict] = None) -> None:
        """Add request to install packages."""
        pkgs = ", ".join(f'"{pkg}"' for pkg in args)
        if extra:
            pkgs += f", {self._2lua(extra)}"
        self._sh.run(f"echo 'Install({pkgs})' >> '{self._fpath}'")

    def uninstall(self, *args: str, extra: typing.Optional[dict] = None) -> None:
        """Add request to uninstall packages."""
        pkgs = ", ".join(f'"{pkg}"' for pkg in args)
        if extra:
            pkgs += f", {self._2lua(extra)}"
        self._sh.run(f"echo 'Uninstall({pkgs})' >> '{self._fpath}'")

    def package(self, name: str, extra: typing.Optional[dict] = None) -> None:
        """Add request to uninstall packages."""
        self._sh.run(f"echo 'Package(\"{name}\", {self._2lua(extra)})' >> '{self._fpath}'")


class Pkglist(_Setup):
    """Setup tool to install packages from given package list."""

    def __init__(self, shell: cli.Shell, *pkglists: str):
        self._sh = shell
        self.pkglists = pkglists

    def prepare(self, revert_needed: bool = True):
        # TODO use UCI setup instead here
        for pkglist in self.pkglists:
            self._sh.run(f"uci add_list pkglists.pkglists.pkglist='{pkglist}'")
        self._sh.run("uci commit pkglists.pkglists")
        pkgupdate(self._sh)

    def revert(self):
        for pkglist in self.pkglists:
            self._sh.run(f"uci del_list pkglists.pkglists.pkglist='{pkglist}'")
        self._sh.run("uci commit pkglists.pkglists")
        pkgupdate(self._sh)
