import pytest


def no_test_help(board, board_uboot):
    board.serial_miniterm()


def test_cpu_env(board, board_uboot):
    assert board_uboot.run("printenv cpu")
    assert board_uboot.output == "cpu=armv7"


@pytest.mark.board("mox")
def test_skip(board_uboot):
    assert board_uboot.run("help")
    assert board_uboot.run("boot")


#def test_access(
