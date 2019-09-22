import pytest


def test_terminal(board, board_shell):
    board.serial_miniterm()


@pytest.mark.board("mox")
def test_skip(board_uboot):
    assert board_uboot.run("help")
    assert board_uboot.run("boot")


#def test_access(
