"""Containers management.
"""
import collections.abc
import functools
import logging
import os
import typing
import warnings

import pexpect
import pylxd

from .. import cli, lxd
from .device import Device
from .exceptions import LXDDeviceError
from .image import Image
from .network import NetworkInterface

logger = logging.getLogger(__package__)


class Container:
    """Generic container handle."""

    # TODO log syslog somehow

    def __init__(
        self,
        lxd_client: pylxd.Client,
        image: typing.Union[str, Image],
        device_map: dict = None,
        internet: typing.Optional[bool] = None,
        strict: bool = True,
        name: typing.Optional[str] = None,
    ):
        self._lxd = lxd_client
        self._device_map = device_map
        self._override_wants_internet = internet
        self._strict = strict
        self._devices = dict()
        self._network = None

        self._image = image if isinstance(image, Image) else Image(self._lxd, image)
        self._logger = logging.getLogger(f"{__package__}[{self._image.name if name is None else name}]")

        self.lxd_container = None

    def prepare(self):
        """Create and start container for this object."""
        if self.lxd_container is not None:
            return

        # Collect profiles to be assigned to the container
        profiles = [lxd.PROFILE_ROOT]
        if (self._override_wants_internet is None and self._image.wants_internet) or self._override_wants_internet:
            profiles.append(lxd.PROFILE_INTERNET)
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
        self.lxd_container = self._lxd.containers.create(
            {
                "name": self._container_name(),
                "ephemeral": True,
                "profiles": profiles,
                "devices": self._devices,
                "source": {
                    "type": "image",
                    "alias": self._image.alias(),
                },
            },
            wait=True,
        )
        self.lxd_container.start(wait=True)
        # Added LXD network class
        self._network = NetworkInterface(self)
        logger.debug("Container prepared: %s", self.lxd_container.name)

    def _container_name(self, prefix="nsfarm"):
        # Warning: the other parts of this project rely on this naming convention to identify containers (such as
        # cleanup algorithm). Make sure that you update them when you do changes in this code.
        name = f"{prefix}-{self._image.name}-{os.getpid()}"
        i = 1
        while self._lxd.containers.exists(f"{name}x{i}"):
            i += 1
        name = f"{name}x{i}"
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

    def pexpect(self, command: collections.abc.Iterable[str] = ("/bin/sh",)) -> pexpect.spawn:
        """Returns pexpect handle for command running in container."""
        assert self.lxd_container is not None
        self._logger.debug("Running command: %s", command)
        pexp = pexpect.spawn("lxc", ["exec", self.lxd_container.name, "--"] + list(command))
        pexp.logfile_read = cli.PexpectLogging(logging.getLogger(self._logger.name + str(command)))
        return pexp

    @property
    @functools.lru_cache
    def shell(self):
        """Extension method that provies access to shell in container.
        It caches result so after first call it always returns same instance of Shell.
        This is intended mostly as easy to reach system console. The prefered way of performing tests trough container
        is using pexpect() method as that spawns multiple separate shell instances.
        """
        return cli.Shell(self.pexpect())

    def get_ip(
        self,
        interfaces: typing.Optional[typing.Container] = None,
        versions: typing.Container = frozenset([4, 6]),
    ) -> list:
        """returns list of ipaddress.IP#Interface filtered according to parameters.

        interfaces: Container containing string names of interfaces from which ip addresses will be obtained
        versions: Container containing integer values of IP versions to be obtained

        Returns a list of ip addresses as IPv4Address or IPv6Address classes
        """
        ips = []
        ifs_dict = self.network.addresses
        for iface in interfaces if interfaces else self.network.interfaces:
            for address in ifs_dict[iface]:
                if address.version in versions:
                    ips.append(address)
        return ips

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.cleanup()

    @property
    def name(self) -> typing.Union[str, None]:
        """Name of container if prepared, otherwise None."""
        return self.lxd_container.name if self.lxd_container is not None else None

    @property
    def image(self) -> Image:
        """Allows access to image used for this container."""
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
        """Dict of passed devices from host."""
        return self._devices

    @property
    def network(self) -> dict:
        """network representation, that represents all data connections."""
        return self._network
