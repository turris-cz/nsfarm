import time
import pytest
from nsfarm.lxd import Container, Image
from .test_image import BASE_IMG


def test_new_container(lxd_client):
    """Try to create container for BASE_IMG.
    """
    container = Container(lxd_client, BASE_IMG)
    assert isinstance(container.image, Image)
    assert container.image.name == BASE_IMG
    assert not container.image.wants_internet  # Base image should not have Internet enabled as a baseline
    assert container.device_map == dict()  # We provided no device map thus it has to be empty
    assert container.devices == dict()  # Base image has no devices assigned


def test_new_container_image(lxd_client):
    """Try to create container for BASE_IMG using Image instance.
    """
    image = Image(lxd_client, BASE_IMG)
    container = Container(lxd_client, image)
    assert isinstance(container.image, Image)
    assert container.image.name == BASE_IMG
    assert container.image is image  # This is intentionally 'is' as it should be the same instance


def test_start_stop(lxd_client):
    """Prepare and cleanup container and check that it really creates and removes container.
    """
    container = Container(lxd_client, BASE_IMG)
    assert container.name is None
    container.prepare()

    assert container.name is not None
    assert lxd_client.containers.exists(container.name)

    container.cleanup()

    # It takes some time before it disappears but it should go away
    for _ in range(10):
        if not lxd_client.containers.exists(container.name):
            return
        time.sleep(1)
    assert not lxd_client.containers.exists(container.name)


def test_context(lxd_client):
    """Check if we can correctly work with context.
    """
    with Container(lxd_client, BASE_IMG) as container:
        container.prepare()
        assert lxd_client.containers.exists(container.name)

    # It takes some time before it disappears but it should go away
    for _ in range(10):
        if not lxd_client.containers.exists(container.name):
            return
        time.sleep(1)
    assert not lxd_client.containers.exists(container.name)


# TODO add tests for enabled and disabled internet and for devices
