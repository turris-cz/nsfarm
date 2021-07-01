"""reForis top level page representation objects.
This contains base for all pages as well as overview or about page.
"""
from .. import base


class ReForis(base.Page):
    """Generic reForis page."""

    _HREF = "reforis"

    def notification_close(self):
        """Wait for notification to appear and close it."""
        self.element("//div[@id='alert-container']//button").click()


class Overview(ReForis):
    """Overview page. This page is the index of reForis."""

    _HREF = ReForis._HREF + "/overview"
    _ID = "//h1[text()='Overview']"
