import ipaddress
import contextlib
import socket


def _find_free_port(proto):
    """Simple function that gives us random free port.
    The possible issue is that it might be taken in the meantime but because it is random port that is less likely.
    """
    socktp = {"tcp": socket.SOCK_STREAM, "udp": socket.SOCK_DGRAM}[proto]
    with contextlib.closing(socket.socket(socket.AF_INET, socktp)) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


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
    def hwaddr(self):
        """returns hardware address/mac of interfaces in a dictionary."""
        return {interface: self._network[interface]["hwaddr"] for interface in self._network}

    @property
    def hostname(self):
        """returns hostname of interfaces in a dictionary."""
        return {interface: self._network[interface]["host_name"] for interface in self._network}

    @property
    def addresses(self):
        """returns ip addresses of interfaces in a dictionary of lists, containing ipaddress.IPvXAddresses"""
        interface_addrs = {}
        for interface in self._network:
            interface_addrs[interface] = []
            for address in self._network[interface]["addresses"]:
                # contains list of dictionaries
                interface_addrs[interface].append(ipaddress.ip_interface(f"{address['address']}/{address['netmask']}"))
        return interface_addrs

    @property
    def interfaces(self):
        """returns list of available interfaces"""
        return self._network.keys()

    def proxy_open(self, proto="tcp", address="127.0.0.1", port="80"):
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

    def proxy_close(self, localport, proto="tcp"):
        """Close existing proxy."""
        self._container._logger.debug("Closing proxy %s port: %d", proto, localport)
        del self._container.lxd_container.devices[f"proxy-{proto}-{localport}"]
        self._container.lxd_container.save(wait=True)

    @contextlib.contextmanager
    def proxy(self, *args, **kwargs):
        """Open proxy for limited context.
        This is using proxy_open and proxy_close.
        """
        port = self.proxy_open(*args, **kwargs)
        try:
            yield port
        finally:
            self.proxy_close(port)
