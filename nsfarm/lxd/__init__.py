import logging
from .image import Image
from .container import Container
from . import exceptions


IMAGE_REPO = "https://images.linuxcontainers.org"

PROFILE_ROOT = "nsfarm-root"
PROFILE_INTERNET = "nsfarm-internet"

# Supppress logging of components pylxd uses (we are not interested that much in them)
logging.getLogger("ws4py").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
