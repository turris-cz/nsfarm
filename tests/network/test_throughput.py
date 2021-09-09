"""These tests are doing benchmark of troughput between various ports of router.

The idea is to do minimal benchmark to load connectection. This should discover problems such is when connection is
established but troughput because of timing or stability is minimal. Another proble it discovers is instability under
load.
We do not expect full speed of line. We expect at least 60% of speed here as rule of hand.
"""
import abc
import json
import logging
import warnings

import pytest

import nsfarm
from nsfarm.setup import openwrt

# TODO Add some exclusive locking for these tests between NSFarm instances to ensure that we won't fail these because we
# are running too much instances in paralel of this.

BITS_IN_MBIT = 10 ** 6  # bits in megabits - for conversion purposes
TEST_TIME = 60  # seconds of time to be tested
TEST_INTERVAL = 10  # seconds of measurement intervals


def get_test_data(shell, type):
    """Type is either 'sender' or 'receiver'"""
    data = json.loads(shell.output)
    speed_data = [round(val["sum"]["bits_per_second"] / BITS_IN_MBIT, 2) for val in data["intervals"]]
    client_speed = round(data["end"]["streams"][0][type]["bits_per_second"] / BITS_IN_MBIT, 2)

    return speed_data, client_speed


class ThroughputTest(abc.ABC):
    """Throughput test"""

    logger = logging.getLogger(name="ThroughputTest")

    @pytest.fixture(scope="class", autouse=True)
    def iperf_client(self, client_board):
        """Client is always router."""
        with openwrt.OpkgInstall(client_board, "iperf3"):
            yield client_board

    def test_TCP(self, iperf_server, iperf_client, board_wan, board):
        """Basic TCP throughput test using iperfgit"""
        iperf_server, iperf_server_ip = iperf_server
        # check if there are more than one ip - this should not be possible
        if len(iperf_server_ip) != 1:
            warnings.warn(f"iperf server is having not exactly one ip address. List of ips: {iperf_server_ip}")
        # setting up Daemon server, with JSON output and for only 1 session.
        iperf_server.command(f"iperf3 -1sJ -i {TEST_INTERVAL}")
        # setting up client, adding additional timeout for pexpect
        iperf_client.run(
            f"iperf3 -J -c {iperf_server_ip[0].ip} -i {TEST_INTERVAL}" + f" -t {TEST_TIME}",
            timeout=TEST_TIME * 1.2,
        )
        iperf_server.prompt()
        data_client_speed, client_speed = get_test_data(iperf_client, "sender")
        data_server_speed, server_speed = get_test_data(iperf_server, "receiver")
        # Check if some value is under the required one
        if any(value < board.min_eth_throughput for value in (data_client_speed + data_server_speed)):
            warnings.warn("Speed did not reach the limit in some part of test.")
        maximum = max(data_client_speed + data_server_speed)
        minimum = min(data_client_speed + data_server_speed)
        speed = (client_speed + server_speed) / 2

        self.logger.info(
            f"\n{self.__class__.__name__} measured data [Mbps]:\n"
            f"Speed reached (min/max) : {speed}({minimum}/{maximum})\n"
            f"Server speeds : {data_client_speed}\n"
            f"Client speeds : {data_server_speed}\n"
        )

        assert speed > board.min_eth_throughput


class TestWAN(ThroughputTest):
    """Test of WAN interface only"""

    @pytest.fixture(scope="class", autouse=True)
    def iperf_server(self, isp_container):
        """Server for test"""
        shell = nsfarm.cli.Shell(isp_container.pexpect())
        return shell, isp_container.get_ip(["wan"], versions=[4])


class TestLAN(ThroughputTest):
    """Test of LAN interface only"""

    @pytest.fixture(scope="class", autouse=True)
    def iperf_server(self, lan1_client):
        """Server for test"""
        shell = nsfarm.cli.Shell(lan1_client.pexpect())
        return shell, lan1_client.get_ip(["lan"], versions=[4])


@pytest.mark.skip
class TestRouting(ThroughputTest):
    """Test of routing from LAN to WAN"""

    @pytest.fixture(scope="class", autouse=True)
    def iperf_client(self, isp_container):
        """Client is always router."""
        shell = nsfarm.cli.Shell(isp_container.pexpect())
        return shell, isp_container.get_ip(["wan"], versions=[4])

    @pytest.fixture(scope="class", autouse=True)
    def iperf_server(self, lan1_client):
        """Server for test"""
        shell = nsfarm.cli.Shell(lan1_client.pexpect())
        return shell, lan1_client.get_ip(["lan"], versions=[4])


# TODO: This test needs dynamic lan interface assignment.
@pytest.mark.skip
class TestSwitching(ThroughputTest):
    """Test of switching in between LAN ports"""

    @pytest.fixture(scope="class", autouse=True)
    def iperf_client(self, test_client):
        """Client is lan device."""
        shell = nsfarm.cli.Shell(test_client.pexpect())
        return shell, test_client.get_ip(["lan"], versions=[4])

    @pytest.fixture(scope="class", autouse=True)
    def iperf_server(self, lan1_client):
        """Server for test"""
        shell = nsfarm.cli.Shell(lan1_client.pexpect())
        return shell, lan1_client.get_ip(["lan"], versions=[4])
