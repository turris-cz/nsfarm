"""Check that all defined images can be bootstrapped. The effect is that they are bootstrapped.
"""
import pytest

from nsfarm.lxd import Image, exceptions
from nsfarm.lxd.utils import all_images


def pytest_generate_tests(metafunc):
    if "image_name" not in metafunc.fixturenames:
        return
    metafunc.parametrize("image_name", all_images())


def test_image_bootstrap(lxd_client, image_name):
    """Test that defined images can be bootstrapped."""
    Image(lxd_client, image_name).prepare()
