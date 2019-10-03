"""Various utility functions to manage NSFarm containers and images.
"""
import os
import logging
from datetime import datetime
import dateutil.parser
from . import container
from . import _lxd


def clean(delta, dry_run=False):
    """Remove all images that were not used for longer then given delta.

    delta: this should be instance of datetime.relativedelta
    dry_run: do not remove anything only report alias of those to be removed on stdout
    """
    _lxd.connect()
    since = datetime.today() - delta

    for img in _lxd.LOCAL.images.all():
        if next((alias for alias in img.aliases if alias["name"].startswith("nsfarm/")), None) is None:
            continue
        last_used = dateutil.parser.parse(
            # Special time "0001-01-01T00:00:00Z" means never used so use upload time instead
            img.last_used_at if not img.last_used_at.startswith("0001-01-01") else img.uploaded_at
        ).replace(tzinfo=None)
        if last_used < since:
            if not dry_run:
                logging.warning("Removing image: %s %s", img.aliases[0]["name"], img.fingerprint)
                img.delete()
            else:
                print(img.aliases[0]["name"])


def all_images():
    """Returns iterator over all known images for NSFarm.

    This collects all *.sh files in imgs directory in root of nsfarm project.
    """
    return (imgf[:-3] for imgf in os.listdir(container.IMGS_DIR) if imgf.endswith(".sh"))


def bootstrap(imgs=None):
    """Bootstrap all defined images.

    imgs: list of images to bootstrap

    Returns True if all images were bootstrapped correctly.
    """
    success = True
    for img in all_images() if imgs is None else imgs:
        logging.info("Trying to bootstrap: %s", img)
        try:
            container.Container(img).prepare_image()
        except Exception as exc:
            success = False
            logging.exception("Bootstrap failed for: %s", img)
    return success
