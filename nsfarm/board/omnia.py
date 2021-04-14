"""Board definitions specific for Turris Omnia
"""
from ._board import Board


class Omnia(Board):
    """Turris Omnia board.
    """

    def _board_bootup(self, uboot):
        uboot.run('setenv bootargs "earlyprintk console=ttyS0,115200 rootfstype=ramfs initrd=0x03000000"')
        uboot.run('tftpboot 0x01000000 192.168.1.1:zImage')
        uboot.run('tftpboot 0x02000000 192.168.1.1:dtb')
        uboot.run('tftpboot 0x03000000 192.168.1.1:root.uimage', timeout=120)
        uboot.sendline('bootz 0x01000000 0x03000000 0x02000000')

    @property
    def wan(self):
        return "eth2"

    @property
    def lan1(self):
        return "lan0"

    @property
    def lan2(self):
        return "lan3"

    @property
    def lan3(self):
        return "lan4"
