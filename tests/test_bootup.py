"""These are test that check that everything we need is running after boot. This does simple and quick tests to catch
general errors such as disabled core services.
"""
import pytest


def test_syslog_ng(client_board):
    """Check that syslog-ng is running by checking if there is /var/log/messages (default log output).
    """
    client_board.run("[ -f /var/log/messages ]")


@pytest.mark.parametrize("process", [
    "crond",
    "dnsmasq",
    "kresd",
    "lighttpd",
    "mosquitto",
    "netifd",
    "odhcpd",
    "rpcd",
    "sshd",
    "syslog-ng",
    "ubusd",
    "watchdog",

])
def test_processes(client_board, process):
    """Check that various essential processes are running.
    """
    client_board.run("pgrep -x '{p}' || pgrep -x \"$(which '{p}')\"".format(p=process))


def test_lighttpd(client_board):
    """Test that there is access to router interface.
    """
    # TODO
