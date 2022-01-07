"""Board definitions specific for Turris Mox
"""
from ._board import Board


class Mox(Board):
    """Turris Mox boards."""

    def _boot_config(self, uboot):
        uboot.run("crc32 04100000 d0630 04effff8")
        uboot.run("mw 04effffc ff325d6a")
        uboot.command("cmp.l 04effff8 04effffc 1")
        if uboot.prompt() == 0:
            return "legacy"
        return None

    @property
    def bootargs(self):
        return super().bootargs + ["console=ttyMV0,115200", "earlycon=ar3700_uart,0xd0012000"]

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
