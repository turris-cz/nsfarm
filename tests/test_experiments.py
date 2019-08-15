import pytest


@pytest.mark.board("omnia")
def test_help(board, board_uboot):
    assert board_uboot.run("help")
    board.serial_miniterm()


def test_date(board_uboot):
    assert board_uboot.run("printenv")


@pytest.mark.board("mox")
def test_skip(board_uboot):
    assert board_uboot.run("help")
    assert board_uboot.run("boot")
