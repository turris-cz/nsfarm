import pytest


def pytest_generate_tests(metafunc):
    if "target" not in metafunc.fixturenames:
        return
    targets = [target for target in metafunc.config.targets.values() if target.is_available()]
    if targets:
        metafunc.parametrize("target", targets, ids=[target.name for target in targets])
    else:
        metafunc.parametrize("target", [pytest.param("no-target", marks=pytest.mark.skip)])
