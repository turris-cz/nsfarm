"""This contains implementations of common actions that are commonly performed in tests on OpenWrt."""
import json

from ..cli import Shell


def service_is_running(service: str, shell: Shell):
    """Verify if there is at least one process running and registered as part of requested service."""
    shell.run(f"ubus -S call service list \"{{'name': '{service}'}}\"")
    result = json.loads(shell.output)
    instances = result.get(service, {}).get("instances", {})
    return bool(instances)
