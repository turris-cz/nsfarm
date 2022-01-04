"""These are common utilities used in tests implementation that control how tests are executed.
"""
import contextlib
import random


@contextlib.contextmanager
def deterministic_random(seed=42):
    """Makes random module somewhat deterministic by setting specific seed every time.
    The state of random generator is preserved during this so you can even nest these.
    """
    state = random.getstate()
    random.seed(seed)
    yield
    random.setstate(state)
