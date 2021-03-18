import pytest
import pkg_resources
import nsfarm.target


def pytest_addoption(parser):
    parser.addoption(
        "-C", "--targets-config",
        help="Path to configuration file with additional targets.",
        metavar="PATH",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    html_plugin = config.pluginmanager.getplugin("html")
    if html_plugin is not None and \
            pkg_resources.parse_version(html_plugin.__version__) >= pkg_resources.parse_version("2.1.0"):
        config.pluginmanager.register(HTMLReport())
    # Parse target cgnfiguration
    targets = nsfarm.target.Targets(config.getoption("-C") or (), rootdir=config.rootdir)
    setattr(config, "targets", targets)


class HTMLReport:
    """Hooks for optional Pytest HTML plugin.
    (Pytest fails in case there is hooks with unknown handler. This way we include it only if we have pytest-html.)
    """

    def pytest_html_report_title(self, report):
        report.title = "NSFarm tests report"
