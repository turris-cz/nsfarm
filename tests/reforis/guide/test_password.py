"""Test the first common step in guide.
"""
import pytest

from nsfarm.web import reforis


def test_index(webdriver, screenshot):
    """Checks that first dialog we get is actually a password configuration"""
    webdriver.get("http://192.168.1.1")
    assert reforis.admin.Password(webdriver).verify()
    screenshot(webdriver, "index", "Default page on unconfigured router")


def test_next(webdriver, screenshot):
    """Check that we can't initially go to the next page or to skip guide. Password setting is required."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()
    assert "disabled" in guide.next.cls
    assert "disabled" in guide.skip.cls
    screenshot(webdriver, "guide-ctl", "Guide control buttons are disabled")


def set_password(request, client_board, webdriver):
    """Sets test password for reForis."""

    def cleanup():
        client_board.run("uci del foris.auth.password && uci commit foris")

    testpass = "testpassword"
    password = reforis.admin.Password(webdriver)
    password.new1.send_keys(testpass)
    password.new2.send_keys(testpass)
    request.addfinalizer(cleanup)
    password.save.click()


def test_password(request, client_board, webdriver, screenshot):
    """Test first dialog for password configuration."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()

    set_password(request, client_board, webdriver)

    guide.wait4ready()
    screenshot(webdriver, "password", "Password was set")
    guide.notification_close()

    client_board.run("uci get foris.wizard.passed")
    assert "password" in client_board.output.split()

    guide.next.click()
    assert reforis.guide.Workflow(webdriver).verify()  # We should end up on workflow page


@pytest.mark.xfail(reason="Guide skip is not possible on password dialogue even when it could be")
def test_skip_after_password(request, client_board, webdriver):
    """Test first dialog for password configuration."""
    guide = reforis.guide.Guide(webdriver)
    guide.go()

    set_password(request, client_board, webdriver)

    guide.wait4ready()
    guide.notification_close()

    guide.skip.click()
    assert reforis.Overview(webdriver).verify()  # We should end up on workflow page


# TODO we should verify that it is possible to change language
