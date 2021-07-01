"""reForis guide page objects.
"""
from .. import ec
from .top import ReForis


class Guide(ReForis):
    """Guide control and other wrapper features added on top of basic dialogues."""

    _HREF = ReForis._HREF + "/guide"
    _ID = "//div[@id='guide-container']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "next": "//span[text()='Next step']/..",
        "skip": "//span[text()='Skip guide']/..",
    }

    def wait4ready(self, timeout=10):
        """Wait for ready to go to next step."""
        self.next.wait(ec.element_has_class, "disabled", True, timeout=timeout)


class Workflow(ReForis):
    """Guide workflow selection."""

    _HREF = ReForis._HREF + "/guide/profile"
    _ID = "//h1[text()='Guide Workflow']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "router": "//div[@id='workflow-selector']/div/div[1]//button",
        "minimal": "//div[@id='workflow-selector']/div/div[2]//button",
        "server": "//div[@id='workflow-selector']/div/div[3]//button",
    }


class Finished(ReForis):
    """Guide finished page."""

    _HREF = ReForis._HREF + "/guide/finished"
    _ID = "//h2[text()='Guide Finished']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "cont": "//button[text()='Continue']",
    }
