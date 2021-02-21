"""Devices management and assigment to containers.
"""
import abc


class Device(abc.ABC):
    """Generic device handler for LXD container.

    This is device handler that can be assigned to containers.
    Depending on exclusivity the assigment might be possible only to one container. In such case to acquire device
    causes original owner to be automatically frozen.
    """

    def __init__(self, exclusive=False):
        self._exclusive = exclusive
        self._assignment = []
        self._def = self._definition()

    def acquire(self, container):
        """Acquire device for new container.

        Returns LXD device definition for this device.
        """
        assert container not in self._assignment
        if self._exclusive and self._assignment:
            # TODO freeze is not implemented
            self._assignment[-1].freeze()
        self._assignment.append(container)
        return self._def

    def release(self, container):
        """Release device from container.
        """
        assert container in self._assignment
        if self._exclusive and container == self._assignment[-1] and len(self._assignment) > 1:
            # TODO unfreeze is not implemented
            self._assignment[-2].unfreeze()
        self._assignment.remove(container)

    @abc.abstractmethod
    def _definition(self):
        """This method has to be implemented by child class and should return definition of device that is later
        provided to caller as result of calling acquire().
        """

    @property
    def container(self):
        """Returns handle for container currently assigned to. If device is free then it returns None.
        """
        if self._assignment:
            return self._assignment[-1]
        return None


class NetInterface(Device):
    """Handler to manage single network interface.
    """

    def __init__(self, link_name, link_iface):
        self._link_name = link_name
        self._link_iface = link_iface
        super().__init__(exclusive=True)

    def _definition(self):
        return {
            f"net:{self._link_name}": {
                "name": self._link_name,
                "nictype": "physical",
                "parent": self._link_iface,
                "type": "nic"
            },
        }


class CharDevice(Device):
    """Handler to manage character device.
    """

    def __init__(self, dev_path, uid=0, gid=0, mode=0o0660):
        self._dev_path = dev_path
        self._uid = uid
        self._gid = gid
        self._mode = mode
        super().__init__()

    def _definition(self):
        return {
            f"char:{self._dev_path}": {
                "source": self._dev_path,
                "uid": str(self._uid),
                "gid": str(self._gid),
                "mode": str(self._mode),
                "type": "unix-char"
            },
        }
