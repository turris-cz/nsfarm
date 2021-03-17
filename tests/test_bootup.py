"""These are test that check that everything we need is running after boot. This does simple and quick tests to catch
general errors such as disabled core services.
"""
import pytest
from nsfarm.toolbox import service_is_running
from nsfarm.cli import Shell


def test_syslog_ng(client_board):
    """Check that syslog-ng is running by checking if there is /var/log/messages (default log output).
    """
    client_board.run("[ -f /var/log/messages ]")


@pytest.mark.parametrize("process", [
    "crond",
    "dnsmasq",
    pytest.param("kresd", marks=pytest.mark.not_board("turris1x")),
    pytest.param("unbound", marks=pytest.mark.board("turris1x")),
    "lighttpd",
    "mosquitto",
    "netifd",
    "odhcpd",
    "rpcd",
    "sshd",
    "syslog-ng",
    "ubusd",
])
def test_processes(client_board, process):
    """Check that various essential processes are running.
    """
    client_board.run(f"pgrep -x '{process}' || pgrep -x \"$(which '{process}')\"")


@pytest.mark.parametrize("service", [
    "cron",
    "dnsmasq",
    "kresd",
    "foris-controller",
    "foris-ws",
    "fosquitto",
    "haveged",
    "lighttpd",
    "network",
    "odhcpd",
    "rpcd",
    "sshd",
    "syslog-ng",
    "sysntpd",
    "umdns",
])
def test_services(client_board, service):
    """Check that various essential processes are running.
    """
    assert service_is_running(service, client_board)


def test_lighttpd(lan1_client):
    """Test that there is access to router interface.
    """
    pexp = Shell(lan1_client.pexpect())
    pexp.run("wget 192.168.1.1 && rm index.html")
