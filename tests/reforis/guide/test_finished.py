"""Test finished configuration in guide.
"""
import pytest

from nsfarm.web import reforis

from .test_net import STEP


@pytest.fixture(name="workflow", autouse=True, params=["router", "min", "bridge"])
def fixture_workflow(request, client_board):
    """Select workflow."""
    cmds = [
        "uci set foris.wizard=config",
        "uci add_list foris.wizard.passed=password",
        "uci add_list foris.wizard.passed=profile",
    ]
    if request.param != "min":
        cmds += [
            "uci add_list foris.wizard.passed=networks",
            f"uci add_list foris.wizard.passed={STEP[request.param]}",
            "uci add_list foris.wizard.passed=time",
            "uci add_list foris.wizard.passed=dns",
            "uci add_list foris.wizard.passed=updater",
        ]
    cmds += [f"uci set foris.wizard.workflow='{request.param}'", "uci commit foris"]
    client_board.run(" && ".join(cmds))
    yield request.param
    # The revert is performed by fixture reset_guide


def test_index(webdriver, screenshot):
    """Check that new page redirects us to correct DNS configuration."""
    webdriver.get("http://192.168.1.1")
    reforis.guide.Finished(webdriver).verify()
    screenshot(webdriver, "index", "Index page when guide is finished.")


def test_finish(client_board, webdriver):
    """Just click continue."""
    reforis.guide.Guide(webdriver).go()
    reforis.guide.Finished(webdriver).cont.click()

    assert reforis.Overview(webdriver).verify()

    client_board.run("uci get foris.wizard.passed")
    assert "finished" in client_board.output.split()
    client_board.run("uci get foris.wizard.finished")
    assert client_board.output == "1"
