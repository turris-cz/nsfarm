"""Containers management.
"""
import os
import typing
import logging
import pexpect
from .. import cli
from .connection import LXDConnection
from .image import Image
from .device import Device

logger = logging.getLogger(__package__)


class Container:
    """Generic container handle.
    """
    # TODO log syslog somehow

    def __init__(self, lxd_connection: LXDConnection, image: typing.Union[str, Image], devices: typing.List[Device] = (),
                 internet: bool = True):
        self.image_name = image.name if isinstance(image, Image) else image
        self._lxd = lxd_connection
        self._internet = internet
        self._devices = tuple(devices)

        self._logger = logging.getLogger(f"{__package__}[{self.image_name}]")
        self.image = image if isinstance(image, Image) else Image(lxd_connection, image)

        self.lxd_container = None

    def prepare(self):
        """Create and start container for this object.
        """
        if self.lxd_container is not None:
            return
        self.image.prepare()

        # Collect profiles to be assigned to container
        profiles = [self._lxd.ROOT_PROFILE, ]
        if self._internet:
            profiles.append(self._lxd.INTERNET_PROFILE)
        # Collect devices to attach to container
        devices = dict()
        for device in self._devices:
            devices.update(device.acquire(self))

        # Create and start container
        self.lxd_container = self._lxd.local.containers.create({
            'name': self._container_name(),
            'ephemeral': True,
            'profiles': profiles,
            'devices': devices,
            'source': {
                'type': 'image',
                'alias': self.image.alias(),
            },
        }, wait=True)
        self.lxd_container.start(wait=True)
        logger.debug("Container prepared: %s", self.lxd_container.name)

    def _container_name(self, prefix="nsfarm"):
        name = f"{prefix}-{self.image_name}-{os.getpid()}"
        if self._lxd.local.containers.exists(name):
            i = 1
            while self._lxd.local.containers.exists(f"{name}-{i}"):
                i += 1
            name = f"{name}-{i}"
        return name

    def cleanup(self):
        """Remove container if it exists.

        This is intended to be called as a cleanup handler. Please call it when you are removing this container.
        """
        if self.lxd_container is None:
            return  # No cleanup is required
        logger.debug("Removing container: %s", self.lxd_container.name)
        # First freeze and remove devices
        self.lxd_container.freeze(wait=True)
        self.lxd_container.devices = dict()
        self.lxd_container.save()
        for device in self._devices:
            device.release(self)
        # Now stop container (Note: container is ephemeral so it is removed automatically after stop)
        self.lxd_container.stop()
        self.lxd_container = None

    def pexpect(self, command=("/bin/sh",)):
        """Returns pexpect handle for command running in container.
        """
        assert self.lxd_container is not None
        self._logger.debug("Running command: %s", command)
        pexp = pexpect.spawn('lxc', ["exec", self.lxd_container.name] + list(command))
        pexp.logfile_read = cli.PexpectLogging(logging.getLogger(self._logger.name + str(command)))
        return pexp

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.cleanup()

    @property
    def name(self) -> typing.Union[str, None]:
        """Name of container if prepared, otherwise None.
        """
        if self.lxd_container is None:
            return None
        return self.lxd_container.name

    @property
    def internet(self) -> bool:
        """If host internet connection should be accessible in this instance.
        """
        return self._internet

    @property
    def devices(self) -> typing.Tuple[Device]:
        """List of passed devices from host.
        """
        return tuple(self._devices)
