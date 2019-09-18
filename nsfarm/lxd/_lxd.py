"""Internal global LXD handle
"""
import pylxd

IMAGES_SOURCE = "https://images.linuxcontainers.org"

# Global LXD handles
IMAGES = None
LOCAL = None


def _profile_device(profile, checkfunc):
    return True not in {checkfunc(dev) for _, dev in profile.devices.items()}


def connect():
    """Make sure that we are connected to LXD.
    """
    global IMAGES
    if IMAGES is None:
        IMAGES = pylxd.Client(IMAGES_SOURCE)
    global LOCAL
    if LOCAL is None:
        LOCAL = pylxd.Client()
        # Verify profiles
        root = LOCAL.profiles.get("nsfarm-root")
        internet = LOCAL.profiles.get("nsfarm-internet")
        if _profile_device(root, lambda dev: dev["type"] == "disk"):
            # TODO better exception
            raise Exception("nsfarm-root does not provide disk device")
        if _profile_device(internet, lambda dev: dev["type"] == "nic" and dev["name"] == "internet"):
            # TODO better exception
            raise Exception("nsfarm-internet does not provide appropriate nic")
