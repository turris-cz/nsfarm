"""Basic DHCP tests for IPv4.

Tested:
- leasetime
- range of assigned ip addresses
- amount of assigned ip addrses
- duplicit address assigment
"""

import abc
import contextlib
import ipaddress
import re
import warnings
import pytest
import nsfarm.lxd
import nsfarm.cli


def ip_within_range(ip, ip_min, ip_max):
    """Returns if IP address is within <min, max) ip addresses
    """
    assert ip_min < ip_max, "ip_within_range(ip, ip_min, ip_max): Wrong assignment of ip_max and ip_min!"
    return ip >= ip_min and ip < ip_max


class DHCPv4Common(abc.ABC):
    nof_clients: int
    dhcp_subnet: ipaddress.IPv4Network
    dhcp_start: int  # starting range of IP addresses - avoid addresses of static leases (usually lan1_client has .10)
    dhcp_limit: int
    dhcp_timeout: int  # Maximum time in which have to be assigned IP address. In RFC2131 is example with 60s

    @property
    def ip_range(self):
        return self.dhcp_subnet[self.dhcp_start], self.dhcp_subnet[self.dhcp_start+self.dhcp_limit]

    @pytest.fixture(name="ip_addresses")
    def fixture_ip_addresses(self, dhcp_clients):
        """Restarts udhcpc client and returns IPv4 addresses of clients. Uses only 'lan' interface.
        """
        for client in dhcp_clients:
            client.shell.run("udhcpc -i lan -t 1 -n", None)
        return [iface.ip for iface in sum([client.get_ip(['lan'], [4]) for client in dhcp_clients], [])]

    @pytest.fixture(name="dhcp_clients", scope="class")
    def fixture_dhcp_clients(self, lxd_client, device_map):
        """fixture starts specific number of clients on lan1 and returns them in list
        """
        cont = "client-dhcp"
        dev_map = {"net:lan": device_map["net:lan1"]}
        with contextlib.ExitStack() as stack:
            yield [stack.enter_context(nsfarm.lxd.Container(lxd_client, cont, dev_map))
                   for _ in range(self.nof_clients)]

    @pytest.fixture(name="save_dhcp_settings", scope="module")
    def fixture_save_dhcp_settings(self, client_board):
        """Saves values of board DHCP settungs, to be restored after dhcp testing.
        """
        list_settings = ['dhcp.']
        pre_test = dict()
        client_board.run(f"uci show dhcp.lan")
        values = client_board.output
        pre_test = dict(setting.strip().split('=', maxsplit=1) for setting in values.split('\n') if setting)

        yield

        client_board.run(f"uci show dhcp.lan")
        for setting in values.split('\n'):
            option, value = setting.strip().split('=', maxsplit=1)
            if option not in pre_test:
                client_board.run(f"uci del {option}")

        for setting, value in pre_test.items():
            if setting in list_settings:
                # it is a list value
                client_board.run(f"uci del {setting}")
                for val in value.split("' '"):
                    val = val.strip(" '")
                    client_board.run(f"uci add_list {setting}='{val}'")
            else:
                value.strip("'")
                client_board.run(f"uci set {setting}='{value}'")
        client_board.run("uci commit")
        client_board.run("/etc/init.d/dnsmasq restart")

    @pytest.fixture(name="configured_board", scope="class", autouse="True")
    def fixture_configured_board(self, client_board, dhcp_clients, save_dhcp_settings):
        """Provides basic configuration of board for dhcp test.
        """
        def obtain_addresses():
            for client in dhcp_clients:
                client.shell.command("udhcpc -i lan -n -A 60")
            for client in dhcp_clients:
                client.shell.prompt()

        # Setup dhcp
        client_board.run(" && ".join([f"uci set dhcp.lan.start='{self.dhcp_start}'",
                                      f"uci set dhcp.lan.limit='{self.dhcp_limit}'",
                                      "uci set dhcp.lan.ignore='1'",
                                      "uci commit dhcp"]))

        # restart board and clients to clean any assigned ip addresses
        client_board.run("/etc/init.d/dnsmasq restart")
        obtain_addresses()
        client_board.run("rm -f /tmp/dhcp.leases /tmp/dhcp.leases.dynamic")
        # enable DHCP
        client_board.run("uci set dhcp.lan.ignore='0' && uci commit")
        client_board.run("/etc/init.d/dnsmasq restart")
        # obtain ip addresses where it is possible.
        obtain_addresses()
        return client_board


class TestIPv4Addresses(DHCPv4Common):
    """Basic test with small amount of clients that exceed DHCP limit.
    """
    nof_clients = 12
    dhcp_subnet = ipaddress.ip_network("192.168.1.0/24")
    dhcp_start = 50
    dhcp_limit = 10
    dhcp_timeout = 60  # seconds

    def test_dhcp_ip_range(self, configured_board, dhcp_clients, ip_addresses):
        """Testing if proper range of ip addresses were set.
        """
        assert ip_addresses, "No addresses were assigned"
        assert not [ip for ip in ip_addresses if not ip_within_range(ip, self.ip_range[0], self.ip_range[1])], \
            f"One or more addresses are out of range of {self.ip_range[0]} to {self.ip_range[1]}." + \
            "\nAssigned addresses:" + "\n".join([ip for ip in ip_addresses])

    def test_dhcp_ip_limit(self, configured_board, dhcp_clients, ip_addresses):
        """Test to check amount of assigned ips
        """
        assert ip_addresses, "No addresses were assigned"
        assert len(ip_addresses) == min(self.dhcp_limit, self.nof_clients), \
            f"Assigned unexpected amount of addresses. Expected: {self.dhcp_limit}, assigned[{len(ip_addresses)}]" + \
            "\nAssigned addresses:" + "\n".join([ip for ip in ip_addresses])

    def test_dhcp_no_duplicit_addresses(self, configured_board, dhcp_clients, ip_addresses):
        """Tests if there are no duplicit addresses
        """
        assert ip_addresses, "No addresses were assigned"
        duplicit_addresses = set([str(ip) for ip in ip_addresses if ip_addresses.count(ip) > 1])
        assert not duplicit_addresses, f"Duplicit addresses : " + "\n".join(duplicit_addresses)


class TestDHCPv4Leasetime(DHCPv4Common):
    nof_clients = 5
    dhcp_subnet = ipaddress.ip_network("192.168.1.0/24")
    dhcp_start = 100
    dhcp_limit = 5
    dhcp_timeout = 60  # seconds

    @pytest.mark.parametrize("leasetime", [122,  # minimum leasetime
                                           2**32-1])  # maximum leasetime
    def test_dhcp_leasetime(self, configured_board, dhcp_clients, leasetime):
        """Testing leasetime using dhcp client.

        While it is using udhcpc on client, it is specific for Alpine linux client.
        """
        # set leasetime
        configured_board.run(f"uci set dhcp.lan.leasetime='{leasetime}' && uci commit")
        configured_board.run(f"uci set dhcp.lan.limit='{self.nof_clients}' && uci commit")
        configured_board.run(f"/etc/init.d/dnsmasq restart")
        # obtain leasetime
        for client in dhcp_clients:
            client.shell.command(f'udhcpc -i lan -n -t 4 -T {self.dhcp_timeout//4} -A {self.dhcp_timeout}')
        client_leases = []
        for client in dhcp_clients:
            client.shell.prompt(timeout=self.dhcp_timeout)
            lst = re.search(r"(?<=(lease time ))\d+\w?", client.shell.output)
            client_leases.append(int(lst.group(0)) if lst else None)

        assert [lst if lst == leasetime else False for lst in client_leases].count(leasetime) == \
            min(self.dhcp_limit, self.nof_clients), \
            f"Invalid leasetimes assigned. Tested: {leasetime}, obtained: " + str(client_leases).strip('[] ')
