import pytest
from nsfarm.lxd import Image, exceptions

BASE_IMG = "base-alpine"
NOEX_IMG = "no-such-image"


def test_new_image(lxd_client):
    """Test public attributes set by Image.__init__
    """
    img = Image(lxd_client, BASE_IMG)
    assert img.name == BASE_IMG
    assert img.lxd_image is None


def test_image_prepare(lxd_client):
    """Test image preparation and lxd_image attribute it should set.
    """
    img = Image(lxd_client, BASE_IMG)
    img.prepare()
    assert img.lxd_image is not None
    assert img.is_prepared()


def test_nonexisting_image(lxd_client):
    """Try to initialize Image for undefined image name.
    """
    with pytest.raises(exceptions.LXDImageUndefinedError):
        Image(lxd_client, NOEX_IMG)
