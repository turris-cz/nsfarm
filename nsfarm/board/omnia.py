"""Board definitions specific for Turris Omnia
"""
from ._board import Board


class Omnia(Board):
    """Turris Omnia board."""

    def _legacy_boot(self, uboot, container_cli):
        container_cli.run("cp 'root/boot/zImage' '/var/tftpboot/'")
        container_cli.run("cp -L 'root/boot/dtb' '/var/tftpboot/'")
        container_cli.run("mkimage -A arm -O linux -T ramdisk -C none -d root.cpio '/var/tftpboot/root.uimage'")
        uboot.run("tftpboot 0x01000000 192.168.1.1:zImage")
        uboot.run("tftpboot 0x02000000 192.168.1.1:dtb")
        uboot.run("tftpboot 0x03000000 192.168.1.1:root.uimage", timeout=240)
        uboot.sendline("bootz 0x01000000 0x03000000 0x02000000")

    @property
    def bootargs(self):
        return super().bootargs + ["console=ttyS0,115200"]

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
