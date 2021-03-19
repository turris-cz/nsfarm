"""These are shortcuts for various marks. Idea behind this is to give some of the marks combination more descriptive
name.
"""
import pytest

# Exclusive for boards
only_turris1x = pytest.mark.board("turris1x")
only_omnia = pytest.mark.board("omnia")
only_mox = pytest.mark.board("mox")
not_turris1x = pytest.mark.not_board("turris1x")
not_omnia = pytest.mark.not_board("omnia")
not_mox = pytest.mark.not_board("mox")

# Default DNS resolver
kresd = not_turris1x
unbound = only_turris1x

# Board capabalities
rainbow = pytest.mark.board("omnia", "turrix1x")
low_ram = pytest.mark.board("mox")
atsha = pytest.mark.board("omnia", "turrix1x")
otp = pytest.mark.board("mox")
