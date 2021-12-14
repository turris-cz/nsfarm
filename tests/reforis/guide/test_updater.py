"""Test the Updater configuration in guide.
"""
import pytest

from nsfarm.web import reforis

from .test_net import STEP


@pytest.fixture(name="workflow", autouse=True, params=["router", "bridge"])
def fixture_workflow(request, client_board):
    """Select workflow."""
    client_board.run(
        " && ".join(
            [
                "uci set foris.wizard=config",
                "uci add_list foris.wizard.passed=password",
                "uci add_list foris.wizard.passed=profile",
                "uci add_list foris.wizard.passed=networks",
                f"uci add_list foris.wizard.passed={STEP[request.param]}",
                "uci add_list foris.wizard.passed=time",
                "uci add_list foris.wizard.passed=dns",
                f"uci set foris.wizard.workflow='{request.param}'",
                "uci commit foris",
            ]
        )
    )
    return request.param
    # The revert is performed by fixture reset_guide


def test_index(webdriver, screenshot):
    """Check that new page redirects us to correct Updater's configuration."""
    webdriver.get("http://192.168.1.1")
    reforis.packages.UpdateSettings(webdriver).verify()
    screenshot(webdriver, "index", "Index page when DNS is passed.")


def test_save_and_next(client_board, webdriver, screenshot, workflow):
    """Just save update settings and pass to next step."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()

    reforis.packages.UpdateSettings(webdriver).save.click()

    guide.wait4ready()
    screenshot(webdriver, f"updates:{workflow}", f"Updates saved for workflow: {workflow}")
    guide.notification_close()

    client_board.run("uci get foris.wizard.passed")
    assert "dns" in client_board.output.split()

    guide.next.click()
    assert reforis.guide.Finished(webdriver).verify()
