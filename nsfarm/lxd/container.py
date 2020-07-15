"""Containers and images management.
"""
import os
import time
import typing
import itertools
import pathlib
import hashlib
import logging
import pexpect
import pylxd
from .. import cli
from .connection import LXDConnection
from .device import NetInterface

IMAGE_INIT_PATH = "/nsfarm-init.sh"  # Where we deploy initialization script for image

IMGS_DIR = pathlib.Path(__file__).parents[2] / "imgs"

logger = logging.getLogger(__package__)


class Container:
    """Generic container handle.
    """
    # TODO log syslog somehow

    def __init__(self, lxd_connection: LXDConnection, img_name: str, devices: typing.List[NetInterface] = (),
                 internet: bool = True):
        self._lxd = lxd_connection
        self._name = img_name
        self._internet = internet
        self._devices = tuple(devices)
        self._dir_path = IMGS_DIR / img_name
        self._file_path = self._dir_path.with_suffix(self._dir_path.suffix + ".sh")
        self._logger = logging.getLogger(f"{__package__}[{img_name}]")
        # Verify existence of image definition
        if not self._file_path.is_file():
            raise Exception(f"There seems to be no file describing image: {self._file_path}")
        if not self._dir_path.is_dir():
            self._dir_path = None
        # Get parent
        with open(self._file_path) as file:
            # This reads second line of file while initial hash removed
            parent = next(itertools.islice(file, 1, 2))[1:].strip()
        self._parent = None
        if parent.startswith("nsfarm:"):
            self._parent = Container(lxd_connection, parent[7:])
        elif parent.startswith("images:"):
            self._parent = self._lxd.images.images.get_by_alias(parent[7:])
        else:
            raise Exception(f"The file has parent from unknown source: {parent}: {self.fpath}")
        # Calculate identity hash and generate image name
        self._hash = self.__identity_hash()
        self._image_alias = f"nsfarm/{self._name}/{self._hash}"
        # Some empty handles
        self._lxd_image = None
        self._lxd_container = None

    def __identity_hash(self):
        md5sum = hashlib.md5()
        # Parent
        if isinstance(self._parent, Container):
            md5sum.update(self._parent.hash.encode())
        else:
            md5sum.update(self._parent.fingerprint.encode())
        # File defining container
        with open(self._file_path, "rb") as file:
            md5sum.update(file.read())
        # Additional nodes from directory
        if self._dir_path:
            nodes = [path for path in self._dir_path.iterdir() if path.is_dir()]
            while nodes:
                node = nodes.pop()
                path = self._dir_path / node
                md5sum.update(str(node).encode())
                if path.is_dir():
                    nodes += [path for path in node.iterdir() if path.is_dir()]
                elif path.is_file():
                    # For plain file include content
                    with open(path, "rb") as file:
                        md5sum.update(file.read())
                elif path.is_link():
                    # For link include its target as well
                    md5sum.update(str(path.resolve()).encode())
        return md5sum.hexdigest()

    def prepare_image(self):
        """Prepare image for this container if not already prepared.

        You can call this explicitly if you want to prepapre image but this method is automatically called when you
        atempt to prepare container so you don't have to do it.
        """
        if self._lxd_image:
            return
        if self._lxd.local.images.exists(self._image_alias, alias=True):
            self._lxd_image = self._lxd.local.images.get_by_alias(self._image_alias)
            return
        # We do not have appropriate image so prepare it
        logger.warning("Bootstrapping image: %s", self._image_alias)
        image_source = {
            'type': 'image',
        }
        if isinstance(self._parent, Container):
            # We have NSFarm image to base on
            self._parent.prepare_image()
            image_source["alias"] = self._parent._image_alias
        else:
            # We have to pull it from images
            image_source["mode"] = "pull"
            image_source["server"] = self._lxd.IMAGES_SOURCE
            image_source["alias"] = self._parent.fingerprint
        container_name = f"nsfarm-bootstrap-{self._name}-{self._hash}"
        try:
            container = self._lxd.local.containers.create({
                'name': container_name,
                'profiles': ['nsfarm-root', 'nsfarm-internet'],
                'source': image_source
            }, wait=True)
        except pylxd.exceptions.LXDAPIException as elxd:
            # TODO found other way to match reason
            if not str(elxd).endswith("This container already exists"):
                raise
            logger.warning("Other instance is already bootsrapping image probably. "
                            "Waiting for following container to go away: %s", container_name)
            while self._lxd.local.containers.exists(container_name):
                time.sleep(1)
            self.prepare_image()  # possibly get created image or try again
            return
        try:
            # TODO log boostrap process
            # Copy script and files to container
            with open(self._file_path) as file:
                container.files.put(IMAGE_INIT_PATH, file.read(), mode=700)
            if self._dir_path:
                container.files.recursive_put(self._dir_path, "/")
            # Run script to bootstrap image
            container.start(wait=True)
            try:
                res = container.execute([IMAGE_INIT_PATH])
                if res.exit_code != 0:
                    # TODO more appropriate exception and possibly use stderr and stdout
                    raise Exception(f"Image initialization failed: {res}")
                container.files.delete(IMAGE_INIT_PATH)  # Remove init script
            finally:
                container.stop(wait=True)
            # Create and configure image
            self._lxd_image = container.publish(wait=True)
            self._lxd_image.add_alias(self._image_alias, f"NSFarm image: {self._name}")
        finally:
            container.delete()

    def prepare(self):
        """Create and start container for this object.
        """
        if self._lxd_container is not None:
            return
        self.prepare_image()
        # Collect profiles to be assigned to container
        profiles = ['nsfarm-root', ]
        if self._internet:
            profiles.append('nsfarm-internet')
        # Collect devices to attach
        devices = dict()
        for device in self._devices:
            devices.update(device.acquire(self))
        # Create and start container
        self._lxd_container = self._lxd.local.containers.create({
            'name': self._container_name(),
            'ephemeral': True,
            'profiles': profiles,
            'devices': devices,
            'source': {
                'type': 'image',
                'alias': self._image_alias,
            },
        }, wait=True)
        self._lxd_container.start(wait=True)
        self._logger.debug("Container prepared: %s", self._lxd_container.name)
        # TODO we could somehow just let it create it and return from this method and wait later on when we realy need
        # container.

    def _container_name(self, prefix="nsfarm"):
        name = f"{prefix}-{self._name}-{os.getpid()}"
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
        if self._lxd_container is None:
            return  # No cleanup is required
        self._logger.debug("Removing container: %s", self._lxd_container.name)
        # First freeze and remove devices
        self._lxd_container.freeze(wait=True)
        self._lxd_container.devices = dict()
        self._lxd_container.save()
        for device in self._devices:
            device.release(self)
        # Now stop container (Note: container is ephemeral so it is removed automatically after stop)
        self._lxd_container.stop()
        self._lxd_container = None

    def pexpect(self, command=("/bin/sh",)):
        """Returns pexpect handle for command running in container.
        """
        assert self._lxd_container is not None
        self._logger.debug("Running command: %s", command)
        pexp = pexpect.spawn('lxc', ["exec", self._lxd_container.name] + list(command))
        pexp.logfile_read = cli.PexpectLogging(logging.getLogger(self._logger.name + str(command)))
        return pexp

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.cleanup()
    
    @property
    def image_name(self):
        """Name of NSFarm image this container is initialized for.
        """
        return self._name

    @property
    def name(self):
        """Name of container if prepared, otherwise None.
        """
        if self._lxd_container is None:
            return None
        return self._lxd_container.name

    @property
    def internet(self):
        """If host internet connection should be accessible in this instance.
        """
        return self._internet

    @property
    def devices(self):
        """List of passed devices from host.
        """
        return self._devices

    @property
    def hash(self):
        """Identifying Hash of container.

        This is unique identifier generated from container sources and used to check if image can be reused or not.
        """
        return self._hash

    @property
    def image_alias(self):
        """Alias of image for this container.
        """
        return self._image_alias
