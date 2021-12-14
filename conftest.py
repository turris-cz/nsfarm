import logging
import os
import re

import pkg_resources
import pytest
import selenium

import nsfarm.target
import nsfarm.web

logger = logging.getLogger(__package__)


def pytest_addoption(parser):
    parser.addoption(
        "-C",
        "--targets-config",
        help="Path to configuration file with additional targets.",
        metavar="PATH",
    )
    parser.addoption(
        "-T",
        "--target",
        help="Run tests on specified TARGET.",
        metavar="TARGET",
    )
    parser.addoption(
        "--viewgui",
        help="Run vncviewer when ever we start selenium container.",
        action="store_true",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    html_plugin = config.pluginmanager.getplugin("html")
    if html_plugin is not None and (
        pkg_resources.parse_version(html_plugin.__version__) >= pkg_resources.parse_version("2.1.0")
    ):
        config.pluginmanager.register(HTMLReport())
    # Parse target cgnfiguration
    targets = nsfarm.target.Targets(config.getoption("-C") or (), rootdir=config.rootdir)
    setattr(config, "targets", targets)
    # Set selected target (None if there is no such target)
    setattr(config, "target_config", targets.get(config.getoption("-T")))
    # Set if gui viewer should be open when testing using Selenium
    nsfarm.web.Container.open_viewer = config.getoption("--viewgui")


class HTMLReport:
    """Hooks for optional Pytest HTML plugin.
    (Pytest fails in case there is hooks with unknown handler. This way we include it only if we have pytest-html.)
    """

    def pytest_html_report_title(self, report):
        report.title = "NSFarm tests report"

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item):
        pytest_html = item.config.pluginmanager.getplugin("html")
        outcome = yield
        report = outcome.get_result()
        extra = getattr(report, "extra", [])

        for identifier, prop in report.user_properties:
            if identifier == f"png.{report.when}":
                extra.append(pytest_html.extras.png(prop[1], prop[0]))

        report.extra = extra


@pytest.fixture
def screenshot(record_property):
    """This provides function that records screenshot to test results."""

    def __shot(
        source: selenium.webdriver.remote.webdriver.WebDriver,
        name: str,
        reason: str = "Unknown reason",
    ):
        logger.info("Taking screenshot '%s': %s", name, reason)
        when = re.search(r"\((.*)\)$", os.environ["PYTEST_CURRENT_TEST"]).group(1)  # TODO isn't there a better way?
        record_property(f"png.{when}", (name, source.get_screenshot_as_base64()))

    return __shot
