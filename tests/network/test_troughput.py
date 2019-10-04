"""These tests are doing benchmark of troughput between various ports of router.

The idea is to do minimal benchmark to load connectection. This should discover problems such is when connection is
established but troughput because of timing or stability is minimal. Another proble it discovers is instability under
load.
We do not expect full speed of line. We expect at least 60% of speed here as rule of hand.
"""
import pytest
# TODO Add some exclusive locking for these tests between NSFarm instances to ensure that we won't fail these because we
# are running too much instances in paralel of this.


@pytest.mark.skip
def test_iperf():
    """Do quick benchmark using iperf3.
    """
    # TODO use parametrize to switch between -R/_, -u/_
    raise NotImplementedError
