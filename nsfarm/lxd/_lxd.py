"""Internal global LXD handle
"""
import logging
import pylxd

IMAGES_SOURCE = "https://images.linuxcontainers.org"

# Global LXD handles
IMAGES = None
LOCAL = None


def _profile_device(profile, check_func):
    return True not in {check_func(dev) for _, dev in profile.devices.items()}


def connect():
    """Make sure that we are connected to LXD.
    """
    # Suppress logging of pylxd components
    logging.getLogger('ws4py').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    # Initialize LXD connection to linuximages.org
    global IMAGES
    if IMAGES is None:
        IMAGES = pylxd.Client(IMAGES_SOURCE)
    # Initialize LXD connection to local server
    global LOCAL
    if LOCAL is None:
        LOCAL = pylxd.Client()
        # Verify profiles
        for name in ("nsfarm-root", "nsfarm-internet"):
            if not LOCAL.profiles.exists(name):
                # TODO better exception
                raise Exception("Missing required LXD profile: {}".format(name))
        root = LOCAL.profiles.get("nsfarm-root")
        internet = LOCAL.profiles.get("nsfarm-internet")
        if _profile_device(root, lambda dev: dev["type"] == "disk"):
            # TODO better exception
            raise Exception("nsfarm-root does not provide disk device")
        if _profile_device(internet, lambda dev: dev["type"] == "nic" and dev["name"] == "internet"):
            # TODO better exception
            raise Exception("nsfarm-internet does not provide appropriate nic")
