"""Base classes for all other implementations used in web testing.
"""
import abc
import logging
import time

import selenium
from selenium.webdriver.common.by import By as _By
from selenium.webdriver.support import expected_conditions as _ec
from selenium.webdriver.support.ui import WebDriverWait as _Wait

logger = logging.getLogger(__package__)


class Element:
    """Wrapper class around Selenium's WebElement. It provides additional functionality."""

    def __init__(
        self,
        webdriver: selenium.webdriver.remote.webdriver.WebDriver,
        xpath: str,
        timeout=10,
    ):
        self.webdriver = webdriver
        self.xpath = xpath
        self._element = _Wait(self.webdriver, timeout).until(_ec.presence_of_element_located((_By.XPATH, xpath)))

    def __getattr__(self, attr):
        return getattr(self._element, attr)

    def wait(self, expected_condition, *args, timeout=10, **kwargs):
        """Wait for given condition. This is helper just for waiting"""
        _Wait(self.webdriver, timeout).until(expected_condition((_By.XPATH, self.xpath), *args, **kwargs))

    def click(self, timeout=10, retry=5):
        """Click the element.
        This first waits for element being clickable and then it tries to click it.
        The combination of Selenium and React is little bit wonky and sometimes we have to try multiple times and thus
        this also allows set retries. This is required for example for checkboxes.
        """
        self.wait(_ec.element_to_be_clickable, timeout=timeout)
        for _ in range(retry):
            try:
                self._element.click()
                return
            except selenium.common.exceptions.ElementClickInterceptedException as exc:
                logger.debug("Click attempt on '%s' failed: %s", self._element, exc)
                time.sleep(1)

    @property
    def cls(self):
        """The easy way to access list of classes assigned to element."""
        return self._element.get_attribute("class").split()


class Page(abc.ABC):
    """Abstract page representation.

    The child is required to change or expand following class variables:
    _HREF: Hyperlink to this page relative to reForis URL
    _ID: Identifier used to check if user is looking at the correct page.
    _ELEMENTS: All elements exported by page for easy use
    """

    _HREF: str = ""
    _ID: str = "//"
    _ELEMENTS: dict[str, str] = dict()

    def __init__(
        self,
        webdriver: selenium.webdriver.remote.webdriver.WebDriver,
        url: str = "http://192.168.1.1/",
    ):
        self.url = url
        self.webdriver = webdriver

    def __getattr__(self, name):
        if name not in self._ELEMENTS:
            raise AttributeError
        return self.element(self._ELEMENTS[name])

    def _queryfunc(self, xpath):
        @property
        def query(self):
            return self.element(xpath)

        return query

    def go(self):
        """Navigate to this page."""
        self.webdriver.get(self.url + self._HREF)

    def verify(self, timeout=10):
        """Check that we are really looking at this page by locating some specific element.
        Returns boolean.
        """
        try:
            self.element(self._ID, timeout)
            return True
        except selenium.common.exceptions.NoSuchElementException:
            return False

    def element(self, xpath, timeout=10):
        """Locates given element and  returns it."""
        return Element(self.webdriver, xpath, timeout=timeout)
