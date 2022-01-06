"""Test for sentinel-dynfw-client.
"""
import pytest

IPSET = "turris-sn-dynfw-block"


def test_ipset_is_nonempty(client_board):
    """Simply check if ipset dynfw uses contains at least one IP."""
    client_board.run(f"while ! ipset list '{IPSET}' | grep -Fvq 'Number of entries: 0'; do sleep 1; done")


@pytest.fixture
def open_ssh_222(client_board):
    """Opens SSH on port 222 from WAN."""
    client_board.run("uci set firewall.nsfarm_public_ssh=redirect")
    client_board.run("uci set firewall.nsfarm_public_ssh.dest_port=22")
    client_board.run("uci set firewall.nsfarm_public_ssh.src_dport=222")
    client_board.run("uci set firewall.nsfarm_public_ssh.proto=tcp")
    client_board.run("uci set firewall.nsfarm_public_ssh.src=wan")
    client_board.run("uci set firewall.nsfarm_public_ssh.target=DNAT")
    client_board.run("uci commit firewall.nsfarm_public_ssh")
    client_board.run("/etc/init.d/firewall reload")
    yield
    client_board.run("uci delete firewall.nsfarm_public_ssh")
    client_board.run("uci commit firewall.nsfarm_public_ssh")
    client_board.run("/etc/init.d/firewall reload")


def test_attack_unblocked(attacker, board_wan, open_ssh_222):
    """Simply checks if we can access SSH when attacker is not blocked."""
    attacker.command(f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no -p 222 root@{board_wan.network.ip}")
    attacker.expect_exact(f"root@{board_wan.network.ip}'s password:")
    attacker.ctrl_c()
    attacker.prompt()


def test_attack_blocked(attacker, board_wan, open_ssh_222, dynfw_block_attacker):
    """Checks if we can't access SSH when attacker is blocked."""
    attacker.run(
        f"ssh -o ConnectTimeout=3 -p 222 root@{board_wan.network.ip}",
        exit_code=lambda ec: ec == 255,
        timeout=10,
    )
    attacker.output == f"ssh: connect to host {board_wan.network.ip} port 222: Operation timed out\n"
