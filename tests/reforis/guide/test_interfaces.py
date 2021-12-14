"""Test just pass trough interfaces configuration.
"""
import pytest

from nsfarm.web import reforis

from .test_net import NET


@pytest.fixture(name="workflow", autouse=True, params=["router", "bridge"])
def fixture_workflow(request, client_board):
    """Set that we passed workflow selection step in the guide."""
    client_board.run(
        " && ".join(
            [
                "uci set foris.wizard=config",
                "uci add_list foris.wizard.passed=password",
                "uci add_list foris.wizard.passed=profile",
                f"uci set foris.wizard.workflow='{request.param}'",
                "uci commit foris",
            ]
        )
    )
    return request.param
    # The revert is performed by fixture reset_guide


def test_index(webdriver, screenshot):
    """Check that new page redirects us to workflow."""
    webdriver.get("http://192.168.1.1")
    assert reforis.network.Interfaces(webdriver).verify()
    screenshot(webdriver, "index", "Index page when workflow is passed.")


def test_save_and_next(client_board, webdriver, screenshot, workflow):
    """Just save interfaces configuration and pass to next step."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()

    reforis.network.Interfaces(webdriver).save.click()

    guide.wait4ready()
    screenshot(
        webdriver,
        f"interfaces:{workflow}",
        f"Interfaces saved for workflow: {workflow}",
    )

    client_board.run("uci get foris.wizard.passed")
    assert "networks" in client_board.output.split()

    guide.next.click()
    assert NET[workflow](webdriver).verify()
