import pytest
from nsfarm.web import Container
from nsfarm.web.container import DRIVER_PORTS
# pylint: disable=no-self-use


@pytest.fixture(name="webcontainer", scope="module")
def fixture_webcontainer(lxd_connection):
    """Provides nsfarm.web.Container instance.
    """
    with Container(lxd_connection, internet=True, strict=False) as container:
        yield container


@pytest.mark.parametrize('browser', DRIVER_PORTS.keys(), scope="class")
class TestDrivers:
    """Simple tests checking our setup for Selenium.
    """

    @pytest.fixture(scope="class")
    def webdriver(self, webcontainer, browser):
        """Selenium Web Driver with class scope. This way we start browser, run some tests and quit it before we
        continue with another browser.
        """
        with webcontainer.webdriver(browser) as driver:
            yield driver

    def test_turris_cz(self, webdriver, screenshot):
        """Test public attributes set by Image.__init__
        """
        webdriver.get('https://turris.com')
        assert "network devices" in webdriver.title
        screenshot(webdriver, "turris.cz", "Screenshot facility check")
