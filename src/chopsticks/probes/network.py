"""Network connectivity probe implementations."""

import subprocess
from typing import Any

from chopsticks.utils.report import ProbeResult


def check_network_reachability(host: str) -> ProbeResult:
    """Check network reachability to the target host."""
    try:
        # Test LXC connectivity
        result = subprocess.run(
            ["lxc", "exec", host, "--", "echo", "ping"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        
        if result.stdout.strip() == "ping":
            details: dict[str, Any] = {
                "method": "lxc exec",
                "status": "reachable",
            }
            
            # Get IP address
            ip_result = subprocess.run(
                ["lxc", "list", host, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            
            if ip_result.returncode == 0:
                import json
                try:
                    data = json.loads(ip_result.stdout)
                    if data and len(data) > 0:
                        state = data[0].get("state", {})
                        network = state.get("network", {})
                        for iface, info in network.items():
                            if iface != "lo" and info.get("addresses"):
                                for addr in info["addresses"]:
                                    if addr.get("family") == "inet":
                                        details["ip_address"] = addr.get("address")
                                        break
                except Exception:
                    pass
            
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=True,
                message="Host is reachable via LXC",
                details=details,
            )
        else:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message="Unexpected response from host",
            )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="Network Reachability",
            host=host,
            passed=False,
            message="Connection attempt timed out",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="Network Reachability",
            host=host,
            passed=False,
            message=f"Failed to reach host: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="Network Reachability",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )
