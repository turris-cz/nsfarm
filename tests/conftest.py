import pytest
import nsfarm.board
import nsfarm.cli
import nsfarm.lxd

########################################################################################################################
## Resources shared among all tests ####################################################################################

@pytest.fixture(scope="session", name="board", params=[pytest.param(None, marks=pytest.mark.serial)])
def fixture_board(request):
    """Brings board on. Nothing else.
    This is top most fixture for board. It returns board handle.
    """
    brd = nsfarm.board.get_board(request.config)
    brd.power(True)
    request.addfinalizer(lambda: brd.power(False))
    return brd


@pytest.fixture(scope="session", name="wan", params=[pytest.param(None, marks=pytest.mark.wan)])
def fixture_wan(request):
    """Top level fixture used to share WAN interface handler.
    """
    return nsfarm.lxd.NetInterface("wan", request.config.target_config['wan'])


@pytest.fixture(scope="session", name="lan1", params=[pytest.param(None, marks=pytest.mark.lan1)])
def fixture_lan1(request):
    """Top level fixture used to share LAN1 interface handler.
    """
    return nsfarm.lxd.NetInterface("lan", request.config.target_config['lan1'])


########################################################################################################################
## Boot and setup fixtures #############################################################################################

@pytest.fixture(scope="session")
def board_shell(request, board, wan):
    """Boot board to Shell.
    Provides instance of nsfarm.cli.Shell()
    """
    request.addfinalizer(lambda: board.reset(True))
    return board.bootup(wan)


########################################################################################################################
## Standard configuration ##############################################################################################

@pytest.fixture(scope="session")
def basic_config(board_shell, wan, lan1):
    """Basic config we consider general. It provides you with configured WAN and one LAN client.
    """
    raise NotImplementedError
