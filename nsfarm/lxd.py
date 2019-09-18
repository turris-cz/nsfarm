"""Containers management and network interface assigment.
"""
import os
import time
import itertools
import hashlib
import logging
import pylxd
import pexpect
# TODO use LXD project for NSFarm?

IMAGES_SOURCE = "https://images.linuxcontainers.org"
IMAGE_INIT_PATH = "/nsfarm-init.sh"  # Where we deploy initialization script for image

IMGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "imgs")

# Global LXD handles
_images_lxd = None
_lxd = None


def _profile_device(profile, checkfunc):
    return True not in {checkfunc(dev) for _, dev in profile.devices.items()}


def _lxd_connect():
    global _images_lxd
    if _images_lxd is None:
        _images_lxd = pylxd.Client(IMAGES_SOURCE)
    global _lxd
    if _lxd is None:
        _lxd = pylxd.Client()
        # Verify profiles
        root = _lxd.profiles.get("nsfarm-root")
        internet = _lxd.profiles.get("nsfarm-internet")
        if _profile_device(root, lambda dev: dev["type"] == "disk"):
            # TODO better exception
            raise Exception("nsfarm-root does not provide disk device")
        if _profile_device(internet, lambda dev: dev["type"] == "nic" and dev["name"] == "internet"):
            # TODO better exception
            raise Exception("nsfarm-internet does not provide appropriate nic")


class NetInterface():
    """Handler to manage single network interface.
    """

    def __init__(self, link_name):
        self.link_name = link_name


class Container():
    """Generic container handle.
    """

    def __init__(self, name, devices=[], internet=True):
        self._name = name
        self._internet = internet
        self._devices = tuple(devices)
        self._dpath = os.path.join(IMGS_DIR, name)
        self._fpath = self._dpath + ".sh"
        # Verify existence of image definition
        if not os.path.isfile(self._fpath):
            raise Exception("There seems to be no file describing image: {}".format(self._fpath))
        if not os.access(self._fpath, os.X_OK):
            raise Exception("The file describing image is not executable: {}".format(self._fpath))
        if not os.path.isdir(self._dpath):
            self._dpath = None
        # Make sure that we are connected to LXD
        _lxd_connect()
        # Get parent
        with open(self._fpath) as file:
            # This reads second line of file while initial hash removed
            parent = next(itertools.islice(file, 1, 2))[1:].strip()
        self._parent = None
        if parent.startswith("nsfarm:"):
            self._parent = Container(parent[7:])
        elif parent.startswith("images:"):
            self._parent = _images_lxd.images.get_by_alias(parent[7:])
        else:
            raise Exception("The file has parent from unknown source: {}: {}".format(parent, self.fpath))
        # Calculate identity hash and generate image name
        self._hash = self.__identity_hash()
        self._image_alias = "nsfarm/{}/{}".format(self._name, self._hash)
        # Some empty handles
        self._lxd_image = None
        self._lxd_container = None

    def __identity_hash(self):
        md5sum = hashlib.md5()
        if isinstance(self._parent, Container):
            md5sum.update(self._parent.hash.encode())
        else:
            md5sum.update(self._parent.fingerprint.encode())
        with open(self._fpath, "rb") as file:
            md5sum.update(file.read())
        if self._dpath:
            nodes = [os.path.join(self._dpath, node) for node in os.listdir(self._dpath)]
            while nodes:
                node = nodes.pop()
                md5sum.update(node.encode())
                if os.path.isdir(node):
                    nodes += [os.path.join(node, nd) for nd in os.listdir(node)]
                elif os.path.isfile(node):
                    # For plain file include content
                    with open(node, "rb") as file:
                        md5sum.update(file.read())
                elif os.path.islink(node):
                    # For link include its target as well
                    md5sum.update(os.readlink(node).encode())
        return md5sum.hexdigest()

    def _container_name(self, prefix="nsfarm"):
        name = "{}-{}-{}".format(
            prefix,
            self._name,
            os.getpid())
        if _lxd.containers.exists(name):
            i = 1
            while _lxd.containers.exists("{}-{}".format(name, i)):
                i += 1
            name = "{}-{}".format(name, i)
        return name

    def prepare_image(self):
        """Prepare image for this container if not already prepared.

        You can call this explicitly if you want to prepapre image but this method is automatically called when you
        atempt to prepare container so you don't have to do it.
        """
        if self._lxd_image:
            return
        if _lxd.images.exists(self._image_alias, alias=True):
            self._lxd_image = _lxd.images.get_by_alias(self._image_alias)
            return
        # We do not have appropriate image so prepare it
        logging.info("Bootstrapping image: %s", self._image_alias)
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
            image_source["server"] = IMAGES_SOURCE
            image_source["alias"] = self._parent.fingerprint
        container_name = "nsfarm-bootstrap-{}-{}".format(self._name, self._hash)
        try:
            container = _lxd.containers.create({
                'name': container_name,
                'profiles': ['nsfarm-root', 'nsfarm-internet'],
                'source': image_source
            }, wait=True)
        except pylxd.exceptions.LXDAPIException as elxd:
            # TODO found other way to match reason
            if not str(elxd).endswith("This container already exists"):
                raise
            logging.warning("Other instance is already bootsrapping image probably. "
                            "Waiting for following container to go away: %s", container_name)
            while _lxd.containers.exists(container_name):
                time.sleep(1)
            self.prepare_image()  # possibly get created image or try again
            return
        try:
            # Copy script and files to container
            with open(self._fpath) as file:
                container.files.put(IMAGE_INIT_PATH, file.read(), mode=700)
            if self._dpath:
                print(self._dpath)
                container.files.recursive_put(self._dpath, "/")
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
            self._lxd_image = container.publish(wait=True)
            self._lxd_image.add_alias(self._image_alias, "NSFarm: {}".format(self._image_alias))
        finally:
            container.delete()

    def prepare(self):
        """Create and start container for this object.
        """
        if self._lxd_container is not None:
            return
        self.prepare_image()
        profiles = ['nsfarm-root', ]
        if self._internet:
            profiles.append('nsfarm-internet')
        # TODO we could somehow just let it create it and return from this
        # method and wait later on when we realy need container.
        self._lxd_container = _lxd.containers.create({
            'name': self._container_name(),
            'ephemeral': True,
            'profiles': profiles,
            'source': {
                'type': 'image',
                'alias': self._image_alias,
            },
        }, wait=True)
        self._lxd_container.start(wait=True)

    def cleanup(self):
        """Remove container if it exists.

        This is intended to be called as a cleanup handler. Please call it when you are removing this container.
        """
        if self._lxd_container is None:
            return  # No cleanup is required
        self._lxd_container.stop()
        self._lxd_container = None
        # Note: container is ephemeral so it is removed automatically after stop

    def pexpect(self, shell="/bin/sh"):
        """Returns pexpect handle for shell in container.
        """
        assert self._lxd_container is not None
        return pexpect.spawn('lxc', ["exec", self._lxd_container.name, shell])

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, etype, value, traceback):
        self.cleanup()

    @property
    def name(self):
        """Name of container
        """
        return self._name

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

    def image_alias(self):
        """Alias of image for this container.
        """
        return self._image_alias


class BootContainer(Container):
    """Extension for Container handling specific tasks for container used to boot medkit on board.
    """

    # TODO branch or build to pull?
    def __init__(self, *args, **kwargs):
        super().__init__("boot", *args, **kwargs)
