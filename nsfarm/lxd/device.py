"""Devices management and assigment to containers.
"""
import abc
import collections.abc


class Device(abc.ABC):
    """Generic device handler for LXD container.
    """

    def __init__(self, value):
        self.value = value

    @abc.abstractmethod
    def acquire(self, device_map: dict):
        """Acquire device for new container.

        Returns LXD device definition for this device.
        """


class NetInterface(Device):
    """Handler to manage single network interface using MacVLAN.
    """

    def acquire(self, device_map: dict):
        devid = f"net:{self.value}"
        if device_map is None or devid not in device_map:
            return {}
        return {
            "name": str(self.value),
            "nictype": "macvlan",
            "parent": str(device_map[devid]),
            "type": "nic",
        }


class CharDevice(Device):
    """Handler to manage character device.
    """

    def acquire(self, device_map: dict):
        return {
            "source": str(self.value),
            "uid": "0",
            "gid": "0",
            "mode": "0660",
            "type": "unix-char",
        }
