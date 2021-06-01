import ipaddress


class NetworkInterface():
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
        """returns hardware address/mac of interfaces in a dictionary.
        """
        return {interface: self._network[interface]['hwaddr'] for interface in self._network}

    @property
    def hostname(self):
        """returns hostname of interfaces in a dictionary.
        """
        return {interface: self._network[interface]['host_name'] for interface in self._network}

    @property
    def addresses(self):
        """returns ip addresses of interfaces in a dictionary of lists, containing ipaddress.IPvXAddresses
        """
        interface_addrs = {}
        for interface in self._network:
            interface_addrs[interface] = []
            for address in self._network[interface]['addresses']:
                # contains list of dictionaries
                interface_addrs[interface].append(ipaddress.ip_interface(f"{address['address']}/{address['netmask']}"))
        return interface_addrs

    @property
    def interfaces(self):
        """returns list of available interfaces
        """
        return self._network.keys()
