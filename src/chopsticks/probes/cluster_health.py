"""Cluster health probe implementations."""

import subprocess
from typing import Any

from chopsticks.utils.report import ProbeResult
from chopsticks.utils.ssh import RemoteExecutor


def check_microceph_status(host: str, executor: RemoteExecutor | None = None) -> ProbeResult:
    """Check MicroCeph status on the target host."""
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    try:
        result = executor.run(
            host,
            ["microceph", "status"],
            timeout=30,
            check=True,
            use_sudo=True,  # MicroCeph commands require sudo
        )
        
        output = result.stdout.strip()
        details: dict[str, Any] = {"raw_output": output}
        
        # Parse basic info from output
        if "Services:" in output:
            services_line = [line for line in output.split("\n") if "Services:" in line]
            if services_line:
                details["services"] = services_line[0].split("Services:")[1].strip()
        
        if "Disks:" in output:
            disks_line = [line for line in output.split("\n") if "Disks:" in line]
            if disks_line:
                details["disks"] = disks_line[0].split("Disks:")[1].strip()
        
        return ProbeResult(
            probe_name="MicroCeph Status",
            host=host,
            passed=True,
            message="MicroCeph is operational",
            details=details,
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="MicroCeph Status",
            host=host,
            passed=False,
            message="Command timed out after 30 seconds",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="MicroCeph Status",
            host=host,
            passed=False,
            message=f"Failed to get MicroCeph status: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="MicroCeph Status",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )


def check_ceph_status(host: str, executor: RemoteExecutor | None = None) -> ProbeResult:
    """Check detailed Ceph status on the target host."""
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    try:
        result = executor.run(
            host,
            ["ceph", "status"],
            timeout=30,
            check=True,
            use_sudo=True,  # Ceph commands require sudo
        )
        
        output = result.stdout.strip()
        details: dict[str, Any] = {"raw_output": output}
        
        # Check for HEALTH_OK
        health_ok = "HEALTH_OK" in output
        health_warn = "HEALTH_WARN" in output
        health_err = "HEALTH_ERR" in output
        
        if health_ok:
            message = "Ceph cluster is healthy (HEALTH_OK)"
            passed = True
        elif health_warn:
            message = "Ceph cluster has warnings (HEALTH_WARN)"
            passed = False
        elif health_err:
            message = "Ceph cluster has errors (HEALTH_ERR)"
            passed = False
        else:
            message = "Could not determine cluster health status"
            passed = False
        
        details["health_status"] = "OK" if health_ok else "WARN" if health_warn else "ERR" if health_err else "UNKNOWN"
        
        return ProbeResult(
            probe_name="Ceph Status",
            host=host,
            passed=passed,
            message=message,
            details=details,
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="Ceph Status",
            host=host,
            passed=False,
            message="Command timed out after 30 seconds",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="Ceph Status",
            host=host,
            passed=False,
            message=f"Failed to get Ceph status: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="Ceph Status",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )
