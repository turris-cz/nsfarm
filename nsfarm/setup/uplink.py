"""Various setups for uplink (WAN) configuration of router.
"""
import abc
import ipaddress
import typing

from .. import cli
from ._setup import Setup as _Setup


class CommonWAN(_Setup):
    """Abstract base for all WAN configuring setups."""

    def __init__(self, shell: cli.Shell, interface: str = "wan", restart: bool = True):
        self._sh = shell
        self._restart = restart
        self._interface = interface
        self._config: dict[str, str] = {}
        self._previous: dict[str, typing.Optional[str]] = {}

    def prepare(self, revert_needed: bool = True):
        for key, value in self._config.items():
            if revert_needed:
                self._sh.command(f"uci -q get network.{self._interface}.{key}")
                self._previous[key] = None if self._sh.prompt() != 0 else self._sh.output
            self._sh.run(f"uci set network.{self._interface}.{key}={value}")
        self._sh.run(f"uci commit network.{self._interface}")
        if self._restart:
            self._sh.run("/etc/init.d/network restart")

    def revert(self):
        for key, value in self._previous.items():
            if value is None:
                self._sh.run(f"uci del network.{self._interface}.{key}")
            else:
                self._sh.run(f"uci set network.{self._interface}.{key}={value}")
        self._sh.run(f"uci commit network.{self._interface}")
        if self._restart:
            self._sh.run("/etc/init.d/network restart")

    def wait4ping(self, target_ip: str = "172.16.1.1"):
        """Uses ping to wait for network to be ready.
        The default target_ip is the gateway for 'isp-common' container thus pinging up to edge of the Internet.
        """
        self._sh.run(f"while ! ping -c1 -w1 '{target_ip}' >/dev/null 2>&1; do true; done")


class DHCPv4(CommonWAN):
    """Configure WAN interface to obtain IPv4 address from DHCP."""

    def __init__(self, shell: cli.Shell, interface: str = "wan", restart: bool = True):
        super().__init__(shell, interface, restart)
        self._config = {"proto": "dhcp"}

    def wait4route(self):
        """Waiting for default route to be added by DHCP."""
        self._sh.run("while ! ip route | grep -q default; do sleep 1; done")


class StaticIPv4(CommonWAN):
    """Configure WAN interface to use static IPv4."""

    def __init__(
        self,
        shell: cli.Shell,
        network: ipaddress.IPv4Interface = ipaddress.ip_interface("172.16.1.42/12"),
        gateway: ipaddress.IPv4Address = ipaddress.ip_address("172.16.1.1"),
        dns: typing.Optional[ipaddress.IPv4Address] = None,  # In default uses gateway
        interface: str = "wan",
        restart: bool = True,
    ):
        """The dns argument can be None and in such case the gateway is used. This is because it is common that gateway
        also provides DNS resolver.
        The defaults are appropriate for network access using 'isp-common' container.
        """
        super().__init__(shell, interface, restart)
        self.network = network
        self.gateway = gateway
        self.dns = dns
        self._config = {
            "proto": "static",
            "ipaddr": network.ip.compressed,
            "netmask": network.network.netmask.compressed,
            "gateway": gateway.compressed,
            "dns": (dns if dns is not None else gateway).compressed,
        }


class PPPoE(CommonWAN):
    """Configure WAN interface to use PPPoE."""

    def __init__(
        self,
        shell: cli.Shell,
        username: str = "turris",
        password: str = "turris",
        interface: str = "wan",
        restart: bool = True,
    ):
        super().__init__(shell, interface, restart)
        self._config = {
            "proto": "pppoe",
            "username": username,
            "password": password,
        }
