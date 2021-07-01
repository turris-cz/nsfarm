"""Test WAN or LAN configuration in guide.
"""
import pytest
from nsfarm.web import reforis

NET = {"router": reforis.network.Wan, "bridge": reforis.network.Lan}
STEP = {"router": "wan", "bridge": "lan"}


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
                f"uci set foris.wizard.workflow='{request.param}'",
                "uci commit foris",
            ]
        )
    )
    return request.param
    # The revert is performed by fixture reset_guide


def test_index(workflow, webdriver, screenshot):
    """Check that new page redirects us to correct network configuration."""
    webdriver.get("http://192.168.1.1")
    NET[workflow](webdriver).verify()
    screenshot(webdriver, "index", "Index page when interfaces is passed.")


def test_save_and_next(client_board, webdriver, screenshot, workflow):
    """Just save network configuration and pass to next step."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()

    NET[workflow](webdriver).save.click()

    guide.wait4ready()
    screenshot(webdriver, f"network:{workflow}", f"Network saved for workflow: {workflow}")

    client_board.run("uci get foris.wizard.passed")
    assert STEP[workflow] in client_board.output.split()

    guide.next.click()
    assert reforis.admin.RegionAndTime(webdriver).verify()
