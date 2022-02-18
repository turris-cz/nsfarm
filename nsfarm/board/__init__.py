"""Generalizations for all boards nsfarm tests software on."""
from ..target.target import Target as _Target
from .mox import Mox
from .omnia import Omnia
from .turris1x import Turris1x


def get_board(target_config: _Target):
    """Instantiate correct board class depending on target_config."""
    boards = {
        "mox": Mox,
        "omnia": Omnia,
        "turris1x": Turris1x,
    }
    if target_config.board not in boards:
        raise Exception(f"Unknown or unsupported board: {target_config.board}")
    return boards[target_config.board](target_config)  # type: ignore
    # Note: we ignore type hints here as it seems that mypy just evaluates this invalidly. It reports that abstract
    # class Board can't be instantiated but we do not have Board in the list and neither of the classes in the dict are
    # abstract. The error can also be resolved by simply reducing dict to just any two boards. This signals some issue
    # with mypy rather than with code we have here.
