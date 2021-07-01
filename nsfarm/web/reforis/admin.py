"""reForis administration page objects.
"""
from .top import ReForis


class Password(ReForis):
    """Dialog to set password."""

    _HREF = ReForis._HREF + "/administration/password"
    _ID = "//h1[text()='Password']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "current": "//form[1]//label[text()='Current password']/..//input",
        "new1": "//form[1]//label[text()='New password']/..//input",
        "new2": "//form[1]//label[text()='Confirm new password']/..//input",
        "use4root": "//form[1]//input[@type='checkbox']",
        "save": "//form[1]//button[@type='submit']",
    }


class RegionAndTime(ReForis):
    """Dialog to set region and time."""

    _HREF = ReForis._HREF + "/administration/region-and-time"
    _ID = "//h1[text()='Region and Time']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }
