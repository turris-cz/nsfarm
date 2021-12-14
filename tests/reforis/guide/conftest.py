import pytest

import nsfarm.web


@pytest.fixture(name="webdriver", scope="package", params=nsfarm.web.BROWSERS)
def fixture_webdriver(client_board, lan1_webclient, request):
    """Provides access to Selenium's web driver."""
    with lan1_webclient.webdriver(request.param) as driver:
        yield driver


@pytest.fixture(autouse=True)
def fixture_fail_screenshot(request, webdriver, screenshot):
    """Takes screenshot on test failure"""
    failed_before = request.session.testsfailed
    yield
    if failed_before != request.session.testsfailed:
        screenshot(webdriver, "fail", "Screenshot of last state before failure is reported")


@pytest.fixture(autouse=True)
def fixture_reset_guide(client_board):
    """Reverts guide setting to the original values (thus to no guide)"""
    yield
    # Note: wizard might not exist so we mask intentionally here error when it is missing
    client_board.run("uci del foris.wizard; uci commit foris")
