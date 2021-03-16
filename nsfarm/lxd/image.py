"""Images management.
"""
import io
import time
import itertools
import functools
import pathlib
import hashlib
import logging
import pylxd
from .connection import LXDConnection
from .exceptions import LXDImageUndefinedError, LXDImageParentError, LXDImageParameterError
from .device import Device, CharDevice

logger = logging.getLogger(__package__)


class Image:
    """Generic Image handle.
    """
    IMAGE_INIT_PATH = "/nsfarm-init.sh"  # Where we deploy initialization script for image
    IMGS_DIR = pathlib.Path(__file__).parents[2] / "imgs"

    def __init__(self, lxd_connection: LXDConnection, img_name: str):
        self.name = img_name
        self._lxd = lxd_connection
        self._dir_path = self.IMGS_DIR / img_name
        self._file_path = self._dir_path.with_suffix(self._dir_path.suffix + ".sh")

        self.lxd_image = None

        # Verify existence of image definition
        if not self._file_path.is_file():
            raise LXDImageUndefinedError(self.name, self._file_path)
        if not self._dir_path.is_dir():
            self._dir_path = None

        # Get image parameters
        with open(self._file_path) as file:
            file.readline()  # Skip initial shebang
            parent, *params = file.readline()[1:].strip().split()  # The initial character is '#' we want to ignore

        self._parent = None
        if parent.startswith("nsfarm:"):
            self._parent = Image(lxd_connection, parent[7:])
        elif parent.startswith("images:"):
            self._parent = self._lxd.images.images.get_by_alias(parent[7:])
        else:
            raise LXDImageParentError(self.name, parent)

        attributes = {
            "char": CharDevice,
        }
        self._devices = []
        for param in params:
            devtype, value = param.split(':', maxsplit=1)
            if devtype in attributes:
                self._devices.append(attributes[devtype](value))
            else:
                raise LXDImageParameterError(self.name, param)

    @functools.lru_cache(maxsize=1)
    def hash(self) -> str:
        """Identifying Hash for latest image.

        This is unique identifier generated from image sources and used to check if image can be reused or not.
        """
        md5sum = hashlib.md5()
        # Parent
        if isinstance(self._parent, Image):
            md5sum.update(self._parent.hash().encode())
        else:
            md5sum.update(self._parent.fingerprint.encode())
        # File defining container
        self._md5sum_update_file(md5sum, self._file_path)
        # Additional nodes from directory
        if self._dir_path:
            nodes = [path for path in self._dir_path.iterdir()]
            while nodes:
                node = nodes.pop()
                path = self._dir_path / node
                md5sum.update(str(node).encode())
                if path.is_dir():
                    nodes += [path for path in node.iterdir()]
                elif path.is_file():
                    # For plain file include content
                    self._md5sum_update_file(md5sum, path)
                elif path.is_symlink():
                    # For link include its target as well
                    md5sum.update(str(path.resolve()).encode())
        return md5sum.hexdigest()

    @staticmethod
    def _md5sum_update_file(md5sum, file_path):
        with open(file_path, "rb") as file:
            # IMPROVE: with Python 3.8 this can we rewritten with := syntax
            while True:
                data = file.read(io.DEFAULT_BUFFER_SIZE)
                if not data:
                    break
                md5sum.update(data)

    def alias(self, img_hash: str = None) -> str:
        """Alias for latest image. This is name used to identify image in LXD.

        img_hash: specific hash (not latest one) to generate alias for.
        """
        if img_hash is None:
            img_hash = self.hash()
        return f"nsfarm/{self.name}/{img_hash}"

    def devices(self) -> list:
        """Returns tuple with additional devices to be included in container.
        These are not-exclusive devices.
        """
        parent_devices = self._parent.devices() if isinstance(self._parent, Image) else tuple()
        # TODO what to do with duplicates?
        return parent_devices + tuple(self._devices)

    def is_prepared(self, img_hash: str = None) -> bool:
        """Check if image we need is prepared.

        img_hash: specific hash (not latest one) to be checked.
        """
        return self._lxd.local.images.exists(self.alias(img_hash), alias=True)

    def prepare(self):
        """Prepare image. It creates it if necessary and populates lxd_image attribute.
        """
        if self.lxd_image is not None:
            return
        if self.is_prepared(self.hash()):
            self.lxd_image = self._lxd.local.images.get_by_alias(self.alias())
            return

        logger.debug("Want to bootstrap image: %s", self.alias())

        image_source = {
            'type': 'image',
        }
        if isinstance(self._parent, Image):
            # We have NSFarm image to base on
            self._parent.prepare()
            image_source["alias"] = self._parent.alias()
        else:
            # We have to pull it from images
            image_source["mode"] = "pull"
            image_source["server"] = self._lxd.IMAGES_SOURCE
            image_source["alias"] = self._parent.fingerprint

        container_name = f"nsfarm-bootstrap-{self.name}-{self.hash()}"
        logger.warning("Bootstrapping image '%s': %s", self.alias(), container_name)

        try:
            container = self._lxd.local.containers.create({
                'name': container_name,
                'profiles': ['nsfarm-root', 'nsfarm-internet'],
                'source': image_source
            }, wait=True)
        except pylxd.exceptions.LXDAPIException as elxd:
            if not str(elxd).endswith("already exists"):
                raise
            logger.warning("Other instance is already bootsrapping image probably. "
                           "Waiting for following container to go away: %s", container_name)
            while self._lxd.local.containers.exists(container_name):
                time.sleep(1)
            self.prepare()  # possibly get created image or try again
            return

        try:
            self._deploy_files(container)
            self._run_bootstrap(container)
            # Create and configure image
            self.lxd_image = container.publish(wait=True)
            self.lxd_image.add_alias(self.alias(), f"NSFarm image: {self.name}")
        finally:
            container.delete()

    def _deploy_files(self, container):
        with open(self._file_path) as file:
            container.files.put(self.IMAGE_INIT_PATH, file.read(), mode=700)
        if self._dir_path:
            container.files.recursive_put(self._dir_path, "/")

    def _run_bootstrap(self, container):
        # TODO log boostrap process
        container.start(wait=True)
        try:
            res = container.execute([self.IMAGE_INIT_PATH])
            if res.exit_code != 0:
                # TODO more appropriate exception and possibly use stderr and stdout
                raise Exception(f"Image initialization failed: {res}")
            container.files.delete(self.IMAGE_INIT_PATH)  # Remove init script
        finally:
            container.stop(wait=True)
