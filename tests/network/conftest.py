import pytest


@pytest.fixture(name="save_dhcp_settings", scope="module")
def fixture_save_dhcp_settings(client_board):
    """Saves values of board DHCP settungs, to be restored after dhcp testing."""
    list_settings = ["dhcp."]
    pre_test = dict()
    client_board.run(f"uci show dhcp.lan")
    values = client_board.output
    pre_test = dict(setting.strip().split("=", maxsplit=1) for setting in values.split("\n") if setting)

    yield

    client_board.run(f"uci show dhcp.lan")
    for setting in values.split("\n"):
        option, value = setting.strip().split("=", maxsplit=1)
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
