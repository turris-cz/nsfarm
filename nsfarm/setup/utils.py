"""Generic utilities that work on all Unix-like platforms as they are based on pure shell operations.
"""
import pathlib
import random
import string
import typing

from .. import cli
from ._setup import Setup as _Setup


class Dir(_Setup):
    """Preparation of directory, generates and on exit cleans or removes the directory of non-existing ones."""

    def __init__(self, shell: cli.Shell, path: typing.Union[str, pathlib.PurePosixPath], expect_empty: bool = True):
        """shell: shell used for setup
        path: path to directory to be created
        expect_empty: if we expect to be empty on removal (rmdir) or if we should remove content (rm -rf)
        """
        self._sh = shell
        self._path = pathlib.PurePosixPath(path)
        self._existed: typing.Optional[pathlib.PurePosixPath] = None
        self.expect_empty = expect_empty

    def prepare(self, revert_needed: bool = True):
        self._sh.run(f'( path=\'{self._path}\'; while [ ! -d "$path" ]; do path="${{path%/*}}"; done; echo "$path" )')
        self._existed = pathlib.PurePosixPath(self._sh.output.strip())
        if self._existed != self._path:  # No need to create existing directory
            self._sh.run(f"mkdir -p '{self._path}'")

    def revert(self):
        if self._existed == self._path:
            return
        if self.expect_empty:
            self._sh.run(f"( cd '{self._existed}' && rmdir -p '{self._path.relative_to(self._existed)}' )")
        else:
            to_remove = pathlib.PurePosixPath(*self._path.parts[: len(self._existed.parts) + 1])
            self._sh.run(f"rm -rf '{to_remove}'")


class DeployFile(_Setup):
    """Simple way to deploy file trough shell instance."""

    def __init__(
        self,
        shell: cli.Shell,
        path: typing.Union[str, pathlib.PurePosixPath],
        content: typing.Union[str, bytes],
        mkdir: bool = False,
    ):
        """shell: shell used for setup
        path: path where file should be deployed
        content: content of file to be deployed
        mkdir: if upper directory should be created or not
        """
        self._sh = shell
        self._path = pathlib.PurePosixPath(path)
        self._content = content
        self._previous: typing.Optional[bytes] = None
        self._dir = Dir(shell, self._path.parent) if mkdir else None

    def prepare(self, revert_needed: bool = True):
        self._previous = self._sh.bin_read(self._path, expect_exist=False) if revert_needed else None
        if self._previous is None and self._dir is not None:
            self._dir.prepare()
        if isinstance(self._content, str):
            self._sh.txt_write(self._path, self._content)
        else:
            self._sh.bin_write(self._path, self._content)

    def revert(self):
        if self._previous is None:
            self._sh.run(f"rm -f '{self._path}'")
            if self._dir is not None:
                self._dir.revert()
        else:
            self._sh.bin_write(self._path, self._previous)


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
