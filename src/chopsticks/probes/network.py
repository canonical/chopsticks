"""Network connectivity probe implementations."""

import subprocess
from typing import Any

from chopsticks.utils.report import ProbeResult
from chopsticks.utils.ssh import RemoteExecutor


def check_network_reachability(host: str, executor: RemoteExecutor | None = None) -> ProbeResult:
    """Check network reachability to the target host."""
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    return executor.test_connectivity(host)
