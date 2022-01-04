"""Tests for LineBytesAggregate that it correctly splits bytes to lines.
"""
import sys

import pytest
from lorem_text import lorem

from nsfarm.cli import LineBytesAggregate
from nsfarm.toolbox.tests import deterministic_random


@pytest.fixture(name="aggregate")
def fixture_aggregate():
    collected = []
    aggregate = LineBytesAggregate(collected.append)
    return aggregate, collected


@pytest.mark.parametrize("delimiter", [b"\n", b"\r", b"\n\r", b"\r\n", b"\r\r\n", b"\r\n\r\r"])
class TestSplits:
    """Test our ability to split stream to lines based on different delimiters."""

    with deterministic_random() as _:
        lorem = [lorem.sentence().encode() for i in range(7)]

    def test_one_call(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it with all data at once."""
        agg, collected = aggregate
        agg.add(delimiter.join(self.lorem))
        assert collected == self.lorem[:-1]
        agg.flush()
        assert collected == self.lorem

    def test_by_block(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        data = delimiter.join(self.lorem)
        block = 24
        for i in range(len(data) // block + 1):
            agg.add(data[block * i : min(block * (i + 1), len(data))])
        assert collected == self.lorem[:-1]
        agg.flush()
        assert collected == self.lorem

    def test_by_line(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for line in self.lorem:
            agg.add(line + delimiter)
        assert collected == self.lorem

    def test_by_line_delay(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for line in self.lorem:
            agg.add((b"" if line is self.lorem[0] else delimiter) + line)
        assert collected == self.lorem[:-1]
        agg.flush()
        assert collected == self.lorem

    def test_by_char(self, aggregate, delimiter):
        """Test that we correctly parse it if we call it multiple times with same sized blockes."""
        agg, collected = aggregate
        for byte in delimiter.join(self.lorem):
            agg.add(byte.to_bytes(1, byteorder=sys.byteorder))
        assert collected == self.lorem[:-1]
        agg.flush()
        assert collected == self.lorem


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
