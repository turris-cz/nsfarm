import pytest
from nsfarm.lxd import Image, exceptions

BASE_IMG = "base-alpine"
NOEX_IMG = "no-such-image"


def test_new_image(connection):
    """Test public attributes set by Image.__init__
    """
    img = Image(connection, BASE_IMG)
    assert img.name == BASE_IMG
    assert img.lxd_image is None


def test_image_prepare(connection):
    """Test image preparation and lxd_image attribute it should set.
    """
    img = Image(connection, BASE_IMG)
    img.prepare()
    assert img.lxd_image is not None
    assert img.is_prepared()


def test_nonexisting_image(connection):
    """Try to initialize Image for undefined image name.
    """
    with pytest.raises(exceptions.LXDImageUndefined):
        Image(connection, NOEX_IMG)
