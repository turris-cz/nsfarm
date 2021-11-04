"""Extended LXD container implementation just for Selenium container.
"""
import contextlib
import subprocess
import typing
import pylxd

import selenium.webdriver

from ..lxd import Container as LXDContainer

IMAGE = "selenium"

DRIVER_PORTS = {
    "firefox": 4444,
    "chrome": 9515,
}

# Standard resolution of view in container
RESOLUTION = [1366, 769]


class Container(LXDContainer):
    """Container with WebDrivers to run Selenium tests against."""

    open_viewer = False

    def __init__(
        self,
        lxd_client: pylxd.Client,
        device_map: dict = None,
        internet: typing.Optional[bool] = None,
        strict: bool = True,
    ):
        super().__init__(lxd_client, IMAGE, device_map, internet, strict)
        self._viewer = None
        self._viewer_port = None

    def prepare(self):
        super().prepare()
        self.shell.run("wait4boot")
        if self.open_viewer and self._viewer is None:
            self._viewer_port = self.network.proxy_open(port=5900)
            self.shell.run("wait4tcp 5900")
            self._logger.info("Running: vncviewer localhost:%d", self._viewer_port)
            self._viewer = subprocess.Popen(["vncviewer", f"localhost:{self._viewer_port}"])

    def cleanup(self):
        if self._viewer is not None:
            self._viewer.terminate()
            self.network.proxy_close(self._viewer_port)
            self._viewer = None
        super().cleanup()

    @contextlib.contextmanager
    def webdriver(self, browser: str = "firefox") -> selenium.webdriver.remote.webdriver.WebDriver:
        """Returns new selenium instance for specified browser.
        The currently supported browsers are:
        * firefox
        * chrome
        """
        with self.network.proxy(port=DRIVER_PORTS[browser]) as localport:
            self.shell.run(f"wait4tcp '{DRIVER_PORTS[browser]}'")
            webdriver = selenium.webdriver.remote.webdriver.WebDriver(f"http://127.0.0.1:{localport}")
            webdriver.set_window_rect(0, 0, *RESOLUTION)
            yield webdriver
            webdriver.quit()
