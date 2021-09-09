"""This contains implementations of common actions that are commonly performed in tests on Alpine.
"""


def network_connect(shell, target: str, port: int, udp: bool = False):
    """Basic netcat connection - only connects"""
    shell.run(f"nc -vz{'u' if udp else ''} {target} {port}", None)
    return "succeeded!" in shell.output
