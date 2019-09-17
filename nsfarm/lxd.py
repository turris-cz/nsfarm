"""Containers management and network interface assigment.
"""
import os
import time
import itertools
import hashlib
import logging
import pylxd
import pexpect

IMAGES_SOURCE = "https://images.linuxcontainers.org"
IMAGE_INIT_PATH = "/nsfarm-init.sh"  # Where we deploy initialization script for image

IMGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imgs")

# Global LXD handles
_images_lxd = None
_lxd = None


def _lxd_connect():
    global _images_lxd
    if _images_lxd is None:
        _images_lxd = pylxd.Client(IMAGES_SOURCE)
    global _lxd
    if _lxd is None:
        _lxd = pylxd.Client()


class NetInterface():
    """Handler to manage single network interface.
    """

    def __init__(self, link_name):
        self.link_name = link_name


class Container():
    """Generic container handle.
    """

    def __init__(self, name):
        self.name = name
        self.dpath = os.path.join(IMGS_DIR, name)
        self.fpath = self.dpath + ".sh"
        # Verify existence of image definition
        if not os.path.isfile(self.fpath):
            raise Exception("There seems to be no file describing image: {}".format(self.fpath))
        if not os.access(self.fpath, os.X_OK):
            raise Exception("The file describing image is not executable: {}".format(self.fpath))
        if not os.path.isdir(self.dpath):
            self.dpath = None
        # Get parent
        self.parent = None
        self.image_parent = None
        with open(self.fpath) as file:
            # This reads parent by reading second line of file while removing
            # first column and at the end striping all white characters.
            parent = next(itertools.islice(file, 1, 2))[1:].strip()
        if parent.startswith("nsfarm:"):
            self.parent = Container(parent[7:])
        elif parent.startswith("images:"):
            # Get remote image handle immediately
            _lxd_connect()
            self.image_parent = _images_lxd.images.get_by_alias(parent[7:])
        else:
            raise Exception("The file has parent from unknown source: {}: {}".format(parent_source, self.fpath))
        # Calculate identity hash
        md5sum = hashlib.md5()
        if self.parent:
            md5sum.update(self.parent.hash.encode())
        else:
            md5sum.update(self.image_parent.fingerprint.encode())
        with open(self.fpath) as file:
            md5sum.update(file.read().encode())
        self.hash = md5sum.hexdigest()
        # Generate image name
        self.image_alias = "nsfarm/{}/{}".format(self.name, self.hash)
        # Some empty handles
        self.lxd_image = None
        self.lxd_container = None

    def _container_name(self, prefix="nsfarm"):
        name = "{}-{}-{}".format(
            prefix,
            self.name,
            os.getpid())
        _lxd_connect()
        if _lxd.containers.exists(name):
            i = 1
            while _lxd.containers.exists("{}-{}".format(name, i)):
                i += 1
            name = "{}-{}".format(name, i)
        return name

    def prepare_image(self):
        """Prepare image for this container if not already prepared.

        You can call this explicitly if you want to prepapre image but this
        method is automatically called when you atempt to prepare container so
        you don't have to do it.
        """
        if self.lxd_image:
            return
        _lxd_connect()
        try:
            self.lxd_image = _lxd.images.get_by_alias(self.image_alias)
            return
        except pylxd.exceptions.NotFound:
            pass
        image_source = {
            'type': 'image',
        }
        if self.parent:
            # We have NSFarm image to base on
            self.parent.prepare_image()
            image_source["alias"] = self.parent.image_alias
        else:
            # We have to pull it from images
            image_source["mode"] = "pull"
            image_source["server"] = IMAGES_SOURCE
            image_source["alias"] = self.image_parent.fingerprint
        container_name = "nsfarm-bootstrap-{}-{}".format(self.name, self.hash)
        try:
            container = _lxd.containers.create({
                'name': container_name,
                'source': image_source
            }, wait=True)
        except pylxd.exceptions.LXDAPIException as elxd:
            # TODO found other way to match reason
            if not str(elxd).endswith("This container already exists"):
                raise
            logging.info("Other instance is already bootsrapping image probably. "
                         "Waiting for following container to go away: %s", container_name)
            while not _lxd.containers.exists(container_name):
                time.sleep(1)
            self.prepare_image()  # possibly get created image or try again
            return
        try:
            # Copy script and files to container
            with open(self.fpath) as file:
                container.files.put(IMAGE_INIT_PATH, file.read(), mode=700)
            if self.dpath:
                container.files.recursive_put(self.dpath, "/")
            # Run script to bootstrap image
            container.start(wait=True)
            try:
                res = container.execute([IMAGE_INIT_PATH])
                if res.exit_code != 0:
                    # TODO more appropriate exception and possibly use stderr and stdout
                    raise Exception("Image initialization failed: {}".format(res))
                container.files.delete(IMAGE_INIT_PATH)  # Remove init script
            finally:
                container.stop(wait=True)
            # Create and configure image
            self.lxd_image = container.publish(wait=True)
            self.lxd_image.add_alias(self.image_alias, "NSFarm: {}".format(self.image_alias))
        finally:
            container.delete()

    def prepare(self):
        """Create and start container for this object.
        """
        if self.lxd_container is not None:
            return
        _lxd_connect()
        self.prepare_image()
        # TODO we could somehow just let it create it and return from this
        # method and wait later on when we realy need container.
        self.lxd_container = _lxd.containers.create({
            'name': self._container_name(),
            'ephemeral': True,
            'source': {
                'type': 'image',
                'alias': self.image_alias,
            },
        }, wait=True)
        self.lxd_container.start(wait=True)

    def cleanup(self):
        """Remove container if it exists.

        This is intended to be called as a cleanup handler. Please call it when
        you are removing this container.
        """
        if self.lxd_container is None:
            return  # No cleanup is required
        self.lxd_container.stop()
        self.lxd_container = None
        # Note: container is ephemeral so it is removed automatically after stop

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.cleanup()

    def pexpect(self, shell="/bin/sh"):
        """Returns pexpect handle for shell in container.
        """
        assert self.lxd_container is not None
        return pexpect.spawn('lxc', ["exec", self.lxd_container.name, shell])


class BootContainer(Container):
    """Extension for Container handling specific tasks for container used to
    boot medkit on board.
    """

    def __init__(self):
        super().__init__("boot")
