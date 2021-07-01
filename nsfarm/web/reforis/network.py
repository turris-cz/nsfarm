"""reForis network page objects.
"""
from .top import ReForis


class Wan(ReForis):
    """WAN interface configuration."""

    _HREF = ReForis._HREF + "/network-settings/wan"
    _ID = "//h1[text()='WAN']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }


class Lan(ReForis):
    """LAN interface configuration."""

    _HREF = ReForis._HREF + "/network-settings/lan"
    _ID = "//h1[text()='LAN']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }


class DNS(ReForis):
    """LAN interface configuration."""

    _HREF = ReForis._HREF + "/network-settings/dns"
    _ID = "//h1[text()='DNS']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }


class Interfaces(ReForis):
    """Network interfaces assigment."""

    _HREF = ReForis._HREF + "/network-settings/interfaces"
    _ID = "//h1[text()='Network Interfaces']"
    _ELEMENTS = {
        **ReForis._ELEMENTS,
        "save": "(//form)[1]//button[@type='submit']",
    }
