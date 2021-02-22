from .mox import Mox
from .omnia import Omnia
from .turris1x import Turris1x
from ..target.target import Target as _Target


def get_board(target_config: _Target):
    """Function which instantiates correct board class depending on target_config.
    """
    boards = {
        "mox": Mox,
        "omnia": Omnia,
        "turris1x": Turris1x,
    }
    if target_config.board not in boards:
        raise Exception(f"Unknown or unsupported board: {target_config.board}")
    return boards[target_config.board](target_config)
