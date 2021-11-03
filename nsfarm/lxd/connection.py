"""LXD connection for NSFarm.
"""
import logging
import pylxd


class LXDConnection:
    """This is generic connection handler for LXD handling both connections to local and images server.
    """
    IMAGES_SOURCE = "https://images.linuxcontainers.org"  # this is needed for remote access via simplestream

    ROOT_PROFILE = "nsfarm-root"
    INTERNET_PROFILE = "nsfarm-internet"

    def __init__(self):
        # Suppress logging of pylxd components
        logging.getLogger('ws4py').setLevel(logging.ERROR)
        logging.getLogger('urllib3').setLevel(logging.ERROR)

        self.local = pylxd.Client()
