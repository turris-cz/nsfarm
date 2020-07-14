"""Internal global LXD handle.
"""
import logging
import pylxd

IMAGES_SOURCE = "https://images.linuxcontainers.org"

ROOT_PROFILE = "nsfarm-root"
INTERNET_PROFILE = "nsfarm-internet"
REQUIRED_PROFILES = (ROOT_PROFILE, INTERNET_PROFILE)

# Global LXD handles
images = None
local = None


def _profile_device(profile, check_func):
    return any(check_func(dev) for dev in profile.devices.values())


def connect():
    """Make sure that we are connected to LXD.
    """
    # Suppress logging of pylxd components
    logging.getLogger('ws4py').setLevel(logging.ERROR)
    logging.getLogger('urllib3').setLevel(logging.ERROR)
    # Initialize LXD connection to linuximages.org
    global images
    if images is None:
        images = pylxd.Client(IMAGES_SOURCE)
    # Initialize LXD connection to local server
    global local
    if local is None:
        local = pylxd.Client()
        # Verify profiles
        for name in REQUIRED_PROFILES:
            if not local.profiles.exists(name):
                # TODO better exception
                raise Exception(f"Missing required LXD profile: {name}")
        root = local.profiles.get(ROOT_PROFILE)
        internet = local.profiles.get(INTERNET_PROFILE)
        if not _profile_device(root, lambda dev: dev["type"] == "disk"):
            # TODO better exception
            raise Exception("nsfarm-root does not provide disk device")
        if not _profile_device(internet, lambda dev: dev["type"] == "nic" and dev["name"] == "internet"):
            # TODO better exception
            raise Exception("nsfarm-internet does not provide appropriate nic")
