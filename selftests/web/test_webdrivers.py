"""Simple test to verify that our Selenium setup works as expected.
"""
import pytest

from nsfarm.web import BROWSERS, Container

# pylint: disable=no-self-use


@pytest.fixture(name="webcontainer", scope="module")
def fixture_webcontainer(lxd_client):
    """Provides nsfarm.web.Container instance."""
    with Container(lxd_client, internet=True, strict=False) as container:
        yield container


@pytest.mark.parametrize("browser", BROWSERS, scope="class")
class TestDrivers:
    """Simple tests checking our setup for Selenium."""

    @pytest.fixture(scope="class")
    def webdriver(self, webcontainer, browser):
        """Selenium Web Driver with class scope. This way we start browser, run some tests and quit it before we
        continue with another browser.
        """
        with webcontainer.webdriver(browser) as driver:
            yield driver

    def test_turris_cz(self, webdriver, screenshot):
        """Test public attributes set by Image.__init__"""
        webdriver.get("https://turris.com")
        assert "network devices" in webdriver.title
        screenshot(webdriver, "turris.cz", "Screenshot facility check")
