"""This module contains configuration and important base data structures.

Every fixture in each test have to reuse one of these fixtures.

Never add different scope to these fixtures. Keep it always as "function" (default)
"""
import pytest
import os
import argparse
import configparser


def pytest_addoption(parser):
    parser.addoption(
        "-T", "--target",
        required=True,
        help="Run tests on target BOARD.",
        metavar="BOARD",
    )
    parser.addoption(
        "-C", "--targets-config",
        help="Path to configuration file with additional targets.",
        metavar="PATH",
    )


def pytest_configure(config):
    # Parse target configuration
    targets = configparser.ConfigParser()
    targets.read(os.path.expanduser("~/.nsfarm_targets.ini"))
    targets.read(os.path.join(config.rootdir, "targets.ini"))
    targets.read(config.getoption("-C") or ())
    # Set target configuration
    target = config.getoption("-T")
    if target not in targets:
        raise Exception("No configuration for target: {}".format(target))
    setattr(config, "target_config", targets[target])


def pytest_runtest_setup(item):
    board = item.config.target_config["board"]
    for boards in item.iter_markers(name="board"):
        if board not in boards.args:
            pytest.skip("test is not compatible with target: {}".format(board))
    for conn in ("serial", "wan", "lan1", "lan2"):
        if item.get_closest_marker(conn) is not None and conn not in item.config.target_config:
            pytest.skip("test requires connection: {}".format(conn))
