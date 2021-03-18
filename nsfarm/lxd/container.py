"""Containers management.
"""
import os
import typing
import logging
import pexpect
import itertools
import warnings
from .. import cli
from .connection import LXDConnection
from .image import Image
from .device import Device
from .exceptions import LXDDeviceError

logger = logging.getLogger(__package__)


class Container:
    """Generic container handle.
    """
    # TODO log syslog somehow

    def __init__(self, lxd_connection: LXDConnection, image: typing.Union[str, Image], device_map: dict = None,
                 internet: typing.Optional[bool] = None, strict: bool = True):
        self._lxd = lxd_connection
        self._internet = False
        self._device_map = device_map
        self._override_wants_internet = internet
        self._strict = strict
        self._devices = dict()

        self._image = image if isinstance(image, Image) else Image(lxd_connection, image)
        self._logger = logging.getLogger(f"{__package__}[{self._image.name}]")

        self.lxd_container = None

    def prepare(self):
        """Create and start container for this object.
        """
        if self.lxd_container is not None:
            return

        # Collect profiles to be assigned to the container
        profiles = [self._lxd.ROOT_PROFILE, ]
        if (self._override_wants_internet is None and self._image.wants_internet) or self._override_wants_internet:
            profiles.append(self._lxd.INTERNET_PROFILE)
        # Collect devices to be attached to the container
        for name, device in self._image.devices().items():
            dev = device.acquire(self._device_map)
            if dev:
                self._devices[name] = dev
                continue
            if self._strict:
                raise LXDDeviceError(name)
            warnings.warn(f"Unable to initialize device: {name}")

        self._image.prepare()

        # Create and start container
        self.lxd_container = self._lxd.local.containers.create({
            'name': self._container_name(),
            'ephemeral': True,
            'profiles': profiles,
            'devices': self._devices,
            'source': {
                'type': 'image',
                'alias': self._image.alias(),
            },
        }, wait=True)
        self.lxd_container.start(wait=True)
        logger.debug("Container prepared: %s", self.lxd_container.name)

    def _container_name(self, prefix="nsfarm"):
        name = f"{prefix}-{self._image.name}-{os.getpid()}"
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
    def image(self) -> Image:
        """Allows access to image used for this container.
        """
        return self._image

    @property
    def device_map(self) -> dict:
        """Provides access to device map this container is using. Note that changes performed after container
        preparation have no effect.
        """
        if self._device_map is None:
            return dict()
        return self._device_map

    @property
    def devices(self) -> typing.Tuple[Device]:
        """Dict of passed devices from host.
        """
        return self._devices
