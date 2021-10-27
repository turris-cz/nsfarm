"""Tests for LineBytesAggregate that it correctly splits bytes to lines.
"""
import sys

import pytest

from nsfarm.cli import LineBytesAggregate


@pytest.fixture(name="aggregate")
def fixture_aggregate():
    collected = []
    aggregate = LineBytesAggregate(collected.append)
    return aggregate, collected


lorem_ipsum = (
    b"Lorem ipsum dolor sit amet,",
    b"consectetur adipiscing elit,",
    b"sed do eiusmod tempor incididunt ut labore et",
    b"dolore magna aliqua. Ut enim ad minim veniam,",
    b"quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea",
    b"commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
    + b"pariatur. Excepteur sint occaecat cupidatat non proident,",
    b"sunt in culpa qui officia deserunt mollit anim id est laborum.",
)


@pytest.mark.parametrize("delimiter", [b"\n", b"\r", b"\n\r", b"\r\n", b"\r\r\n", b"\r\n\r\r"])
class TestSplits:
    """Test our ability to split stream to lines based on different delimiters."""

    def test_one_call(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it with all data at once."""
        agg, collected = aggregate
        agg.add(delimiter.join(lorem_ipsum))
        assert tuple(collected) == lorem_ipsum[:-1]
        agg.flush()
        assert tuple(collected) == lorem_ipsum

    def test_by_block(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        data = delimiter.join(lorem_ipsum)
        block = 24
        for i in range(len(data) // block + 1):
            agg.add(data[block * i : min(block * (i + 1), len(data))])
        assert tuple(collected) == lorem_ipsum[:-1]
        agg.flush()
        assert tuple(collected) == lorem_ipsum

    def test_by_line(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for line in lorem_ipsum:
            agg.add(line + delimiter)
        assert tuple(collected) == lorem_ipsum

    def test_by_line_delay(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for line in lorem_ipsum:
            agg.add((b"" if line is lorem_ipsum[0] else delimiter) + line)
        assert tuple(collected) == lorem_ipsum[:-1]
        agg.flush()
        assert tuple(collected) == lorem_ipsum

    def test_by_char(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for byte in delimiter.join(lorem_ipsum):
            agg.add(byte.to_bytes(1, byteorder=sys.byteorder))
        assert tuple(collected) == lorem_ipsum[:-1]
        agg.flush()
        assert tuple(collected) == lorem_ipsum


def test_real(aggregate):
    """Test on real data as they arrive in blocks as they are produced."""
    agg, collected = aggregate
    comm = (
        b"\x1b]0;root@turris: ~\x07root@turris:~# ",
        b"export PS1='nsfprompt:$(echo -n $?)\\$ '\r\n" b"nsfprompt:0# ",
        b"uci set network.wan.proto='static'\r\n",
        b"nsfprompt:0# ",
        b"uci set network.wan.ipaddr='172.16.1.42'\r\n",
        b"nsfprompt:0# ",
        b"uci set network.wan.netmask='255.240.0.0'\r\n",
        b"nsfprompt:0# ",
        b"uci commit network\r\n",
    )
    for data in comm:
        agg.add(data)
    assert tuple(collected) == (
        b"\x1b]0;root@turris: ~\x07root@turris:~# export PS1='nsfprompt:$(echo -n $?)\\$ '",
        b"nsfprompt:0# uci set network.wan.proto='static'",
        b"nsfprompt:0# uci set network.wan.ipaddr='172.16.1.42'",
        b"nsfprompt:0# uci set network.wan.netmask='255.240.0.0'",
        b"nsfprompt:0# uci commit network",
    )
