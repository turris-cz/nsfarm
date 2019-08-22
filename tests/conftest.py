import pytest
import nsfarm.board
import nsfarm.cli


@pytest.fixture(scope="session", name="board", params=[pytest.param(None, marks=pytest.mark.serial)])
def fixture_board(request):
    """Brings board on. Nothing else.
    This is top most fixture for board. It returns board handle.
    """
    brd = nsfarm.board.get_board(request.config)
    brd.power(True)
    request.addfinalizer(lambda: brd.power(False))
    return brd


@pytest.fixture(scope="session")
def board_uboot(request, board):
    """Boot board to u-boot prompt.
    Provides instance of nsfarm.cli.Uboot()
    """
    request.addfinalizer(lambda: board.reset(True))
    return board.uboot()


@pytest.fixture(scope="session")
def board_shell(request, board):
    """Boot board to Shell.
    Provides instance of nsfarm.cli.Shell()
    """
    request.addfinalizer(lambda: board.reset(True))
    # TODO prepare wan container with appropriate medkit
    return board.bootup()
