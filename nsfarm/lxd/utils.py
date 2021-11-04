"""Various utility functions to manage NSFarm containers and images.
"""
import os
import logging
from datetime import datetime
import dateutil.parser
import pylxd
from .container import Container
from .image import Image

logger = logging.getLogger(__package__)

BOOTSTRAP_LIMIT = dateutil.relativedelta.relativedelta(hours=1)


def clean_images(delta: dateutil.relativedelta.relativedelta, dry_run: bool = False):
    """Remove all images that were not used for longer then given delta.

    delta: this should be instance of datetime.relativedelta
    dry_run: do not remove anything only return aliases of those to be removed

    Returns list of (to be) removed images.
    """
    lxd_client = pylxd.Client()
    since = datetime.today() - delta

    removed = []
    for img in lxd_client.images.all():
        # We remove our images and images without alias as those are pulled images
        if img.aliases and not any(alias["name"].startswith("nsfarm/") for alias in img.aliases):
            continue
        last_used = dateutil.parser.parse(
            # Special time "0001-01-01T00:00:00Z" means never used so use upload time instead
            img.last_used_at if not img.last_used_at.startswith("0001-01-01") else img.uploaded_at
        ).replace(tzinfo=None)
        if last_used < since:
            name = f"{img.aliases[0]['name']}({img.fingerprint})" if img.aliases else img.fingerprint
            removed.append(name)
            if not dry_run:
                logger.warning("Removing image: %s", name)
                img.delete()
    return removed


def _delete_container(cont):
    ephemeral = cont.ephemeral
    if cont.status == "Running":
        cont.stop(wait=True)
    if not ephemeral:
        cont.delete()


def clean_containers(dry_run=False):
    """Remove abandoned containers created by nsfarm.

    dry_run: do not remove anything, only return list of containers names to be removed.

    Returns list of (to be) removed containers.
    """
    lxd_client = pylxd.Client()
    since = datetime.today() - BOOTSTRAP_LIMIT

    removed = []
    for cont in lxd_client.instances.all():
        if not cont.name.startswith("nsfarm-"):
            continue
        if cont.name.startswith("nsfarm-bootstrap-"):
            # We can't simply identify owner of bootstrap container but we can set limit on how long bootstrap should
            # take at most and remove any older containers.
            created_at = dateutil.parser.parse(cont.created_at).replace(tzinfo=None)
            if created_at < since:
                removed.append(cont.name)
                if not dry_run:
                    _delete_container(cont)
        else:
            # Container have PID of process they are spawned by in the name. We can't safely remove any container
            # without running owner process.
            pid = int(cont.name.split('-')[-1].split('x')[0])
            try:
                os.kill(pid, 0)
            except OSError as err:
                if (err.errno != 3):  # 3 == ESRCH: No such process
                    raise
                removed.append(cont.name)
                if not dry_run:
                    _delete_container(cont)
    return removed


def all_images():
    """Returns iterator over all known images for NSFarm.

    This collects all *.sh files in imgs directory in root of nsfarm project.
    """
    return (imgf[:-3] for imgf in os.listdir(Image.IMGS_DIR) if imgf.endswith(".sh"))


def bootstrap(lxd_client, imgs=None):
    """Bootstrap all defined images.

    imgs: list of images to bootstrap

    Returns True if all images were bootstrapped correctly.
    """
    success = True
    for img in all_images() if imgs is None else imgs:
        logger.info("Trying to bootstrap: %s", img)
        Image(lxd_client, img).prepare()
    return success
