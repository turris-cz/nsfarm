"""Common base for all setup classes.
"""
import abc

import pytest


class Setup(abc.ABC):
    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.revert()

    @abc.abstractmethod
    def prepare(self, revert_needed: bool = True) -> None:
        """Prepare defined setup by this class. The argument revert_needed can be used to signal that revert won't
        be called. This is handy if we want to do setup in short lived environment. Setup can skip some steps thanks to
        that.
        """

    @abc.abstractmethod
    def revert(self) -> None:
        """Revert all changes done by this instance."""

    def request(self, request: pytest.FixtureRequest) -> None:
        """Alternative way to prepare and revert correctly the setup. This uses Pytest's request method add_finalizer."""
        self.prepare()
        request.addfinalizer(self.revert)

    def revert_not_needed(self):
        """This is simply prepare called with revert_needed=True. This is more or less for documentation purposes as
        it is shorter and more explicit to call this method over prepare with argument.
        """
        self.prepare(revert_needed=True)
