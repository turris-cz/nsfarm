"""reForis packages page objects.
"""
from .top import ReForis


class UpdateSettings(ReForis):
    """Update settings page."""

    _HREF = ReForis._HREF + "/package-management/update-settings"
    _ID = "//h1[text()='Update Settings']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }
