import pytest
from nsfarm.lxd import Image, exceptions

BASE_IMG = "base-alpine"
NOEX_IMG = "no-such-image"


def test_new_image(lxd_connection):
    """Test public attributes set by Image.__init__
    """
    img = Image(lxd_connection, BASE_IMG)
    assert img.name == BASE_IMG
    assert img.lxd_image is None


def test_image_prepare(lxd_connection):
    """Test image preparation and lxd_image attribute it should set.
    """
    img = Image(lxd_connection, BASE_IMG)
    img.prepare()
    assert img.lxd_image is not None
    assert img.is_prepared()


def test_nonexisting_image(lxd_connection):
    """Try to initialize Image for undefined image name.
    """
    with pytest.raises(exceptions.LXDImageUndefinedError):
        Image(lxd_connection, NOEX_IMG)
