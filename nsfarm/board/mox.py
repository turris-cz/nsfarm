"""Board definitions specific for Turris Mox
"""
from ._board import Board


class Mox(Board):
    """Turris Mox boards."""

    def _board_bootup(self, uboot):
        uboot.run('setenv bootargs "earlyprintk console=ttyMV0,115200 earlycon=ar3700_uart,0xd0012000 rootfstype=ramfs initrd=0x03000000"')
        uboot.run('tftpboot 0x5000000 192.168.1.1:Image')
        uboot.run('tftpboot 0x4f00000 192.168.1.1:armada-3720-turris-mox.dtb')
        uboot.run('tftpboot 0x8000000 192.168.1.1:root.uimage', timeout=120)
        uboot.sendline('booti 0x5000000 0x8000000 0x4f00000')

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
