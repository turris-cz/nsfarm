"""Utility functions for network related operations.
"""
import ipaddress
import typing

from .. import cli


def wait4ping(shell: cli.Shell, target_ip: typing.Union[str, ipaddress.IPv4Address] = "172.16.1.1"):
    """Uses ping to wait for network to be ready.
    The default target_ip is the gateway for 'isp-common' container thus pinging up to edge of the Internet.
    """
    shell.run(f"while ! ping -c1 -w1 '{target_ip}' >/dev/null 2>&1; do true; done")


def wait4route(shell: cli.Shell):
    """Waiting for default route to be available."""
    shell.run("while ! ip route | grep -q default; do sleep 1; done")
