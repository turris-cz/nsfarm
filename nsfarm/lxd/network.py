"""Network abstraction for LXD container."""
import contextlib
import ipaddress
import socket
import typing


def _find_free_port(proto):
    """Provide random unused port.

    The possible issue is that it might be taken in the meantime but because it is random port that is less likely.
    """
    socktp = {"tcp": socket.SOCK_STREAM, "udp": socket.SOCK_DGRAM}[proto]
    with contextlib.closing(socket.socket(socket.AF_INET, socktp)) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


ProtocolTypeStr = typing.Union[typing.Literal["tcp"], typing.Literal["udp"]]


class NetworkInterface:
    """Interface representing network interfaces of LXD container.

    Following values from lxd network dict are not implemented: counters, type, mtus, state
    """

    def __init__(self, container):
        self._container = container

    @property
    def _network(self):
        return self._container.lxd_container.state().network

    @property
    def hwaddr(self) -> dict[str, str]:
        """Return hardware address/mac of interfaces in a dictionary."""
        return {interface: self._network[interface]["hwaddr"] for interface in self._network}

    @property
    def hostname(self) -> dict[str, str]:
        """Return hostname of interfaces in a dictionary."""
        return {interface: self._network[interface]["host_name"] for interface in self._network}

    @property
    def addresses(self) -> dict[str, list[typing.Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]]]:
        """Return ip addresses of interfaces in a dictionary of lists, containing ipaddress.IPvXAddresses."""
        interface_addrs: dict[str, list[typing.Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]]] = {}
        for interface in self._network:
            interface_addrs[interface] = []
            for address in self._network[interface]["addresses"]:
                # contains list of dictionaries
                interface_addrs[interface].append(ipaddress.ip_interface(f"{address['address']}/{address['netmask']}"))
        return interface_addrs

    @property
    def interfaces(self) -> list[str]:
        """Return list of available interfaces."""
        return self._network.keys()

    def proxy_open(
        self,
        proto: ProtocolTypeStr = "tcp",
        address: typing.Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address] = "127.0.0.1",
        port: int = 80,
    ) -> int:
        """Proxy socket connection through container.

        Warning: This supports only TCP and UDP sockets right now!
        Returns local port number service is proxied to.
        """
        assert self._container.lxd_container is not None
        freeport = _find_free_port(proto)
        self._container._logger.debug("Opening proxy to %s:%s:%d on port: %d", proto, address, port, freeport)
        self._container.lxd_container.devices[f"proxy-{proto}-{freeport}"] = {
            "connect": f"{proto}:{address}:{port}",
            "listen": f"{proto}:127.0.0.1:{freeport}",
            "type": "proxy",
        }
        self._container.lxd_container.save(wait=True)
        return freeport

    def proxy_close(self, localport: int, proto: ProtocolTypeStr = "tcp"):
        """Close existing proxy."""
        self._container._logger.debug("Closing proxy %s port: %d", proto, localport)
        del self._container.lxd_container.devices[f"proxy-{proto}-{localport}"]
        self._container.lxd_container.save(wait=True)

    @contextlib.contextmanager
    def proxy(self, *args, **kwargs) -> typing.Generator[int, None, None]:
        """Open proxy for limited context.

        This is using proxy_open and proxy_close.
        """
        port = self.proxy_open(*args, **kwargs)
        try:
            yield port
        finally:
            self.proxy_close(port)
