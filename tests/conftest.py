import pytest
from nsfarm import cli, board

@pytest.fixture(scope="session")
def board_on(request):
    """Brings board on. Nothing else.
    This is top most fixture for board.
    """
    brd = board.get_board(request.config)
    # TODO if we have power switch use it here
    request.addfinalizer(lambda: brd.reset(True))
    return brd


@pytest.fixture(scope="session")
def board_uboot(board_on):
    """Boot board to u-boot prompt.
    """
    board_on.reset(False)
    pexp = board_on.serial_pexpect()
    pexp.expect_exact(["Hit any key to stop autoboot: ", ])
    pexp.sendline("")
    uboot = cli.Uboot(pexp)
    assert uboot.prompt()
    return uboot


@pytest.fixture
def wan_isp(request):
    "Container on WAN port simulating ISP (providing internet connection)."
    # TODO
    pass
