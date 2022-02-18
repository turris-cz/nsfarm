"""Board definitions specific for Turris 1.x."""
from ._board import Board


class Turris1x(Board):
    """Turris 1.0 and 1.1 boards."""

    @property
    def wan(self):
        return "eth0"

    @property
    def lan1(self):
        return "lan1"

    @property
    def lan2(self):
        return "lan3"

    @property
    def lan3(self):
        return "lan4"
