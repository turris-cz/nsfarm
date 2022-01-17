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

import pytest

import nsfarm.cli
import nsfarm.lxd


def ip_within_range(ip, ip_min, ip_max):
    """Returns if IP address is within <min, max) ip addresses"""
    assert ip_min < ip_max, "ip_within_range(ip, ip_min, ip_max): Wrong assignment of ip_max and ip_min!"
    return ip >= ip_min and ip < ip_max


def obtain_addresses(dhcp_clients):
    for client in dhcp_clients:
        client.shell.command("udhcpc -i lan -n -A 60")
    for client in dhcp_clients:
        client.shell.prompt()


class DHCPv4Common(abc.ABC):
    nof_clients: int
    dhcp_subnet: ipaddress.IPv4Network
    dhcp_start: int  # starting range of IP addresses - avoid addresses of static leases (usually lan1_client has .10)
    dhcp_limit: int
    dhcp_timeout: int  # Maximum time in which have to be assigned IP address. In RFC2131 is example with 60s
    dhcp_static_lease_start: int  # Start of leases
    dhcp_static_amount: int  # Amount of static leases to be set.

    @property
    def ip_range(self):
        return (
            self.dhcp_subnet[self.dhcp_start],
            self.dhcp_subnet[self.dhcp_start + self.dhcp_limit],
        )

    @pytest.fixture(name="ip_addresses")
    def fixture_ip_addresses(self, dhcp_clients):
        """Restarts udhcpc client and returns IPv4 addresses of clients. Uses only 'lan' interface."""
        for client in dhcp_clients:
            client.shell.run("udhcpc -i lan -t 1 -n", check=False)
        yield [iface.ip for iface in sum([client.get_ip(["lan"], [4]) for client in dhcp_clients], [])]

    @pytest.fixture(name="dhcp_clients", scope="class")
    def fixture_dhcp_clients(self, lxd_client, device_map):
        """Fixture starts specific number of clients on lan1 and returns them in list"""
        cont = "client"
        dev_map = {"net:lan": device_map["net:lan1"]}
        with contextlib.ExitStack() as stack:
            yield [
                stack.enter_context(nsfarm.lxd.Container(lxd_client, cont, dev_map)) for _ in range(self.nof_clients)
            ]

    @pytest.fixture(name="configured_board", scope="class", autouse=True)
    def fixture_configured_board(self, client_board, dhcp_clients, save_dhcp_settings):
        """Provides basic configuration of board for dhcp test."""
        # Setup dhcp
        client_board.run(
            " && ".join(
                [
                    f"uci set dhcp.lan.start='{self.dhcp_start}'",
                    f"uci set dhcp.lan.limit='{self.dhcp_limit}'",
                    "uci set dhcp.lan.ignore='1'",
                    "uci commit dhcp",
                ]
            )
        )

        # restart board and clients to clean any assigned ip addresses
        client_board.run("/etc/init.d/dnsmasq restart")
        obtain_addresses(dhcp_clients)
        client_board.run("rm -f /tmp/dhcp.leases /tmp/dhcp.leases.dynamic")
        # enable DHCP
        client_board.run("uci set dhcp.lan.ignore='0' && uci commit")
        client_board.run("/etc/init.d/dnsmasq restart")
        # obtain ip addresses where it is possible.
        obtain_addresses(dhcp_clients)

    @pytest.fixture(name="static_leases")
    def fixture_static_leases(self, client_board, dhcp_clients):
        """setups static leases

        the static addresses are set according to two attributes:
            - self.dhcp_static_lease_start
            - self.dhcp_static_amount
        it assignes specified amount of adresses from lease start (including)
        """
        ip_idx = self.dhcp_static_lease_start
        dhcp_static_ids = []
        for client in dhcp_clients[: self.dhcp_static_amount]:
            ip_addr = self.dhcp_subnet[ip_idx].compressed
            commands = [
                f"uci set dhcp.@host[-1].mac={client.network.hwaddr['lan']}",
                f"uci set dhcp.@host[-1].name='{client.network.hostname['lan']}'",
                "uci set dhcp.@host[-1].dns='1'",
                f"uci set dhcp.@host[-1].ip='{ip_addr}'",
            ]
            client_board.run("uci add dhcp host")
            dhcp_static_ids.append(client_board.output)
            client_board.run("&&".join(commands))
            ip_idx += 1
        client_board.run("uci commit dhcp")
        client_board.run("/etc/init.d/dnsmasq restart")
        obtain_addresses(dhcp_clients)

        yield

        for client_id in dhcp_static_ids:
            client_board.run(f"uci del dhcp.{client_id}")
        client_board.run("uci commit dhcp")
        client_board.run("/etc/init.d/dnsmasq restart")
        client_board.run("rm -f /tmp/dhcp.leases /tmp/dhcp.leases.dynamic")
        obtain_addresses(dhcp_clients)


@pytest.mark.deploy
class TestIPv4Essentials(DHCPv4Common):
    """Basic tests with single client to check basic functionality

    checks:
        - client have IP within range
        - basic static lease assignment
    """

    nof_clients = 1
    dhcp_subnet = ipaddress.ip_network("192.168.1.0/24")
    dhcp_start = 50
    dhcp_limit = 10
    dhcp_timeout = 68000
    dhcp_static_lease_start = 65
    dhcp_static_amount = 1

    def test_dhcp_ip_range(self, ip_addresses):
        """Tests if assigned IP is within range"""
        assert ip_addresses, "No address were assigned"
        assert ip_within_range(
            ip_addresses[0], self.ip_range[0], self.ip_range[1]
        ), f"IP {ip_addresses[0]} is not within range of {self.ip_range[0]} {self.ip_range[1]}"

    def test_static_lease(self, dhcp_clients, static_leases, ip_addresses):
        """Test single static address outside range of assigned IP addresses to avoid possible positive negative."""
        assert ip_addresses
        assert (
            self.dhcp_subnet[self.dhcp_static_lease_start] in ip_addresses
        ), "Address not present on DHCP client.\nAddresses present:{ip_addr}"


class TestIPv4Addresses(DHCPv4Common):
    """Basic test with small amount of clients that exceed DHCP limit."""

    nof_clients = 12
    dhcp_subnet = ipaddress.ip_network("192.168.1.0/24")
    dhcp_start = 50
    dhcp_limit = 10
    dhcp_timeout = 60  # seconds
    dhcp_static_lease_start = 58
    dhcp_static_amount = 4

    def test_dhcp_ip_range(self, dhcp_clients, ip_addresses):
        """Testing if proper range of ip addresses were set."""
        assert ip_addresses, "No addresses were assigned"
        assert not [ip for ip in ip_addresses if not ip_within_range(ip, self.ip_range[0], self.ip_range[1])], (
            f"One or more addresses are out of range of {self.ip_range[0]} to {self.ip_range[1]}."
            + "\nAssigned addresses:"
            + "\n".join([ip for ip in ip_addresses])
        )

    def test_dhcp_ip_limit(self, dhcp_clients, ip_addresses):
        """Test to check amount of assigned ips"""
        assert ip_addresses, "No addresses were assigned"
        assert len(ip_addresses) == min(self.dhcp_limit, self.nof_clients), (
            f"Assigned unexpected amount of addresses. Expected: {self.dhcp_limit}, assigned[{len(ip_addresses)}]"
            + "\nAssigned addresses:"
            + "\n".join([ip for ip in ip_addresses])
        )

    def test_dhcp_no_duplicit_addresses(self, dhcp_clients, ip_addresses):
        """Tests if there are no duplicit addresses"""
        assert ip_addresses, "No addresses were assigned"
        duplicit_addresses = set([str(ip) for ip in ip_addresses if ip_addresses.count(ip) > 1])
        assert not duplicit_addresses, f"Duplicit addresses : " + "\n".join(duplicit_addresses)

    def test_dhcp_static_leases(self, static_leases, dhcp_clients, ip_addresses):
        """This tests adds 4 static leases, therefore all clients should have assigned addresses.

        By default these addresses are assigned to first four clients.
        The addresses of static leases are partially from dhcp range and partially outside.
        """
        static_ips = [self.dhcp_subnet[idx + self.dhcp_static_lease_start] for idx in range(self.dhcp_static_amount)]
        assert not [
            True for ip_addr in static_ips if ip_addr not in ip_addresses
        ], "Missing some static IP addresses:\n" + "\n".join(ip_addresses)
        assert not [
            True for ip_addr in ip_addresses if ip_addresses.count(ip_addr) > 1
        ], "Duplicit IP addresses:\n" + "\n".join(ip_addresses)
        assert len(ip_addresses) == 12, "Some addresses were not assigned"


class TestDHCPv4Leasetime(DHCPv4Common):
    nof_clients = 5
    dhcp_subnet = ipaddress.ip_network("192.168.1.0/24")
    dhcp_start = 100
    dhcp_limit = 5
    dhcp_timeout = 60  # seconds

    @pytest.mark.parametrize("leasetime", [122, 2 ** 32 - 1])  # minimum leasetime  # maximum leasetime
    def test_dhcp_leasetime(self, client_board, dhcp_clients, leasetime):
        """Testing leasetime using dhcp client.

        While it is using udhcpc on client, it is specific for Alpine linux client.
        """
        # set leasetime
        client_board.run(f"uci set dhcp.lan.leasetime='{leasetime}' && uci commit")
        client_board.run(f"uci set dhcp.lan.limit='{self.nof_clients}' && uci commit")
        client_board.run(f"/etc/init.d/dnsmasq restart")
        # obtain leasetime
        for client in dhcp_clients:
            client.shell.command(f"udhcpc -i lan -n -t 4 -T {self.dhcp_timeout//4} -A {self.dhcp_timeout}")
        client_leases = []
        for client in dhcp_clients:
            client.shell.prompt(timeout=self.dhcp_timeout)
            lst = re.search(r"(?<=(lease time ))\d+\w?", client.shell.output)
            client_leases.append(int(lst.group(0)) if lst else None)

        assert [lst if lst == leasetime else False for lst in client_leases].count(leasetime) == min(
            self.dhcp_limit, self.nof_clients
        ), f"Invalid leasetimes assigned. Tested: {leasetime}, obtained: " + str(client_leases).strip("[] ")
