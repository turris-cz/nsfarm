from .mox import Mox
from .omnia import Omnia
from .turris1x import Turris1x


def get_board(config):
    """Function which instantiates correct board class depending on target_config.
    """
    boards = {
        "mox": Mox,
        "omnia": Omnia,
        "turris1x": Turris1x,
    }
    board = config.target_config["board"]
    if board not in boards:
        raise Exception("Unknown or unsupported board: {}".format(board))
    return boards[board](config.getoption("-T"), config.target_config)
