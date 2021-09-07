"""This just tests that various basic binaries work (we can run them).

This does not check their functionality but it rather just tests that they can be executed.
"""
import pytest

BINARIES = {
    "opkg": None,
    "pkgupdate": None,
    "wget": None,
    "curl": None,
    "find": "--help",
    "grep": "--help",
}


@pytest.mark.deploy
@pytest.mark.parametrize("binary", BINARIES.keys())
def test_binaries(client_board, binary):
    """Check that various essential processes can be executed."""
    client_board.run(f"'{binary}' {BINARIES[binary] or '--version'}")
