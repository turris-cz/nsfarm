"""These are tests to check that we are able to communicate with board's crypto.
The backend is different depending on board but common crypto-wrapper unites the
attribute access.
"""
import pytest


@pytest.mark.parametrize("hwtype", [
    pytest.param("atsha", marks=pytest.mark.board("omnia", "turris1x")),
    pytest.param("otp", marks=pytest.mark.board("mox")),
])
def test_hw_type(hwtype, client_board):
    """Check if reported hardware type matches board.
    """
    client_board.run("crypto-wrapper hw-type")
    assert client_board.output == hwtype


def test_serial_number(request, client_board):
    """Check that syslog-ng is running by checking if there is /var/log/messages (default log output).
    """
    client_board.run("crypto-wrapper serial-number")
    assert client_board.output == request.config.target_config.serial_number
