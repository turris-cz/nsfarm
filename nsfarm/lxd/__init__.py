import logging

from . import exceptions
from .container import Container
from .image import Image

IMAGE_REPO = "https://images.linuxcontainers.org"

PROFILE_ROOT = "nsfarm-root"
PROFILE_INTERNET = "nsfarm-internet"

# Supppress logging of components pylxd uses (we are not interested that much in them)
logging.getLogger("ws4py").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
