"""Test selection of various workflows and what they activate.
"""
import pytest
from nsfarm.web import reforis


@pytest.fixture(autouse=True)
def fixture_pass_password(client_board):
    """Set that we passed passowrd step in the guide."""
    client_board.run("uci set foris.wizard=config && uci add_list foris.wizard.passed=password && uci commit foris")
    # The revert is performed by fixture reset_guide


def test_index(webdriver, screenshot):
    """Check that new page redirects us to workflow."""
    webdriver.get("http://192.168.1.1")
    assert reforis.guide.Workflow(webdriver).verify()
    screenshot(webdriver, "index", "Index page when password is passed.")


def test_router(client_board, webdriver, screenshot):
    """Select router workflow."""
    workflow = reforis.guide.Workflow(webdriver)
    workflow.go()

    workflow.router.click()

    guide = reforis.guide.Guide(webdriver)
    guide.wait4ready()
    screenshot(webdriver, "router", "Router workflow selected")

    client_board.run("uci get foris.wizard.passed")
    assert "profile" in client_board.output.split()
    client_board.run("uci get foris.wizard.workflow")
    assert client_board.output == "router"

    guide.next.click()
    assert reforis.network.Interfaces(webdriver).verify()  # We should end up on interfaces configuration page


def test_minimal(client_board, webdriver, screenshot):
    """Select minimal workflow."""
    workflow = reforis.guide.Workflow(webdriver)
    workflow.go()

    workflow.minimal.click()

    guide = reforis.guide.Guide(webdriver)
    guide.wait4ready()
    screenshot(webdriver, "minimal", "Minimal workflow selected")

    client_board.run("uci get foris.wizard.passed")
    assert "profile" in client_board.output.split()
    client_board.run("uci get foris.wizard.workflow")
    assert client_board.output == "min"

    guide.next.click()
    assert reforis.guide.Finished(webdriver).verify()  # This makes guide finish


def test_server(client_board, webdriver, screenshot):
    """Select server/bridge workflow."""
    workflow = reforis.guide.Workflow(webdriver)
    workflow.go()

    workflow.server.click()

    guide = reforis.guide.Guide(webdriver)
    guide.wait4ready()
    screenshot(webdriver, "server", "Server workflow selected")

    client_board.run("uci get foris.wizard.passed")
    assert "profile" in client_board.output.split()
    client_board.run("uci get foris.wizard.workflow")
    assert client_board.output == "bridge"

    guide.next.click()
    assert reforis.network.Interfaces(webdriver).verify()  # We should end up on interfaces configuration page
