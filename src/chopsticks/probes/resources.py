"""Resource availability probe implementations."""

import subprocess
from typing import Any

from chopsticks.utils.report import ProbeResult


def check_disk_capacity(host: str) -> ProbeResult:
    """Check disk capacity on the target host."""
    try:
        result = subprocess.run(
            ["lxc", "exec", host, "--", "df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        
        output = result.stdout.strip()
        lines = output.split("\n")
        
        if len(lines) >= 2:
            # Parse df output
            fields = lines[1].split()
            if len(fields) >= 5:
                details: dict[str, Any] = {
                    "filesystem": fields[0],
                    "size": fields[1],
                    "used": fields[2],
                    "available": fields[3],
                    "use_percent": fields[4],
                }
                
                # Check if usage is acceptable (< 90%)
                use_pct = int(fields[4].rstrip("%"))
                passed = use_pct < 90
                
                if passed:
                    message = f"Disk usage is acceptable ({use_pct}%)"
                else:
                    message = f"Disk usage is high ({use_pct}%)"
                
                return ProbeResult(
                    probe_name="Disk Capacity",
                    host=host,
                    passed=passed,
                    message=message,
                    details=details,
                )
        
        return ProbeResult(
            probe_name="Disk Capacity",
            host=host,
            passed=False,
            message="Could not parse disk capacity output",
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="Disk Capacity",
            host=host,
            passed=False,
            message="Command timed out",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="Disk Capacity",
            host=host,
            passed=False,
            message=f"Failed to check disk capacity: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="Disk Capacity",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )


def check_host_resources(host: str) -> ProbeResult:
    """Check host resource availability (CPU, memory)."""
    try:
        # Check memory
        mem_result = subprocess.run(
            ["lxc", "exec", host, "--", "free", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        
        # Check CPU
        cpu_result = subprocess.run(
            ["lxc", "exec", host, "--", "nproc"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        
        details: dict[str, Any] = {}
        
        # Parse memory info
        mem_lines = mem_result.stdout.strip().split("\n")
        if len(mem_lines) >= 2:
            mem_fields = mem_lines[1].split()
            if len(mem_fields) >= 2:
                details["memory_total"] = mem_fields[1]
                details["memory_used"] = mem_fields[2] if len(mem_fields) > 2 else "N/A"
                details["memory_available"] = mem_fields[-1]
        
        # Parse CPU info
        cpu_count = cpu_result.stdout.strip()
        details["cpu_cores"] = cpu_count
        
        # Basic validation: ensure we have at least 2 cores and some memory
        passed = True
        messages = []
        
        try:
            if int(cpu_count) < 2:
                passed = False
                messages.append(f"Low CPU count: {cpu_count} cores")
        except ValueError:
            passed = False
            messages.append("Could not parse CPU count")
        
        if passed:
            message = f"Host resources adequate ({cpu_count} cores)"
        else:
            message = "; ".join(messages)
        
        return ProbeResult(
            probe_name="Host Resources",
            host=host,
            passed=passed,
            message=message,
            details=details,
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="Host Resources",
            host=host,
            passed=False,
            message="Command timed out",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="Host Resources",
            host=host,
            passed=False,
            message=f"Failed to check host resources: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="Host Resources",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )
