"""Board definitions specific for Turris Mox
"""
from ._board import Board


class Mox(Board):
    """Turris Mox boards.
    """

    @property
    def wan(self):
        return "eth0"

    @property
    def lan1(self):
        return "lan1"

    @property
    def lan2(self):
        return "lan4"

    @property
    def lan3(self):
        return "lan10"
