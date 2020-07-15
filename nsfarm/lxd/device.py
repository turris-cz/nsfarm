"""Devices management and assigment to containers.
"""
import abc


class Device(abc.ABC):
    """Generic device handler for LXD container.

    This is device handler that can be assigned to containers. Note that it can be assigned to only one container at the
    time so assigment freezes original container to allow device removal.
    """

    def __init__(self):
        self._assignment = []
        self._def = self._definition()

    def acquire(self, container):
        """Acquire device for new container.

        Returns LXD device definition for this device.
        """
        assert container not in self._assignment
        if self._assignment:
            # TODO freeze is not implemented
            self._assignment[-1].freeze()
        self._assignment.append(container)
        return self._def

    def release(self, container):
        """Release device from container.
        """
        assert container in self._assignment
        if container == self._assignment[-1] and len(self._assignment) > 1:
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
        super().__init__()

    def _definition(self):
        return {
            self._link_name: {
                "name": self._link_name,
                "nictype": "physical",
                "parent": self._link_iface,
                "type": "nic"
            },
        }
