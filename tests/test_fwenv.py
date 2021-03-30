"""This checks that we have correctly configured access to uboot environment using uboot-tools.
"""
import pytest


@pytest.mark.deploy
def test_fw_printenv(client_board):
    """Check that we can access uboot environment.
    """
    client_board.run("fw_printenv")
    assert "Warning: Bad CRC, using default environment" not in client_board.output
