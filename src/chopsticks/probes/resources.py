"""Resource availability probe implementations."""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from chopsticks.utils.report import ProbeResult
from chopsticks.utils.ssh import RemoteExecutor


def parse_memory_to_gb(memory_str: str) -> float:
    """Parse memory string to GB value.
    
    Handles various units: B, KB, MB, GB, KiB, MiB, GiB, etc.
    Examples:
        "16Gi" -> 16.0
        "2048Mi" -> 2.0
        "512M" -> 0.5
        "1024K" -> 0.001
    
    Args:
        memory_str: Memory value with unit (e.g., "16Gi", "2048Mi")
    
    Returns:
        Memory value in GB
    
    Raises:
        ValueError: If format is unrecognized
    """
    # Remove whitespace
    memory_str = memory_str.strip()
    
    # Match number and unit
    match = re.match(r'^([\d.]+)\s*([A-Za-z]+)?$', memory_str)
    if not match:
        raise ValueError(f"Cannot parse memory format: {memory_str}")
    
    value = float(match.group(1))
    unit = (match.group(2) or 'B').upper()
    
    # Conversion factors to GB
    conversions = {
        'B': 1 / (1024 ** 3),
        'K': 1 / (1024 ** 2),
        'KB': 1 / (1024 ** 2),
        'KIB': 1 / (1024 ** 2),
        'M': 1 / 1024,
        'MB': 1 / 1024,
        'MIB': 1 / 1024,
        'G': 1,
        'GB': 1,
        'GIB': 1,
        'T': 1024,
        'TB': 1024,
        'TIB': 1024,
        # Handle lowercase 'i' suffix
        'KI': 1 / (1024 ** 2),
        'MI': 1 / 1024,
        'GI': 1,
        'TI': 1024,
    }
    
    if unit not in conversions:
        raise ValueError(f"Unknown memory unit: {unit}")
    
    return value * conversions[unit]


def check_root_disk_capacity(host: str, executor: RemoteExecutor | None = None) -> ProbeResult:
    """Check root filesystem disk capacity on the target host."""
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    try:
        result = executor.run(
            host,
            ["df", "-h", "/"],
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
                    message = f"Root disk usage is acceptable ({use_pct}%)"
                else:
                    message = f"Root disk usage is high ({use_pct}%)"
                
                return ProbeResult(
                    probe_name="Root Disk Capacity",
                    host=host,
                    passed=passed,
                    message=message,
                    details=details,
                )
        
        return ProbeResult(
            probe_name="Root Disk Capacity",
            host=host,
            passed=False,
            message="Could not parse disk capacity output",
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="Root Disk Capacity",
            host=host,
            passed=False,
            message="Command timed out",
        )
    
    except subprocess.CalledProcessError as e:
        return ProbeResult(
            probe_name="Root Disk Capacity",
            host=host,
            passed=False,
            message=f"Failed to check disk capacity: {e.stderr}",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="Root Disk Capacity",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )


def get_microceph_osd_paths(host: str, executor: RemoteExecutor) -> list[str]:
    """Get OSD data paths from MicroCeph configuration.
    
    Returns a list of OSD data directory paths to check for disk usage.
    """
    paths = []
    
    try:
        # Try to get OSD info from ceph osd df
        result = executor.run(
            host,
            ["ceph", "osd", "df", "--format", "json"],
            timeout=15,
            check=False,
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                # Get number of OSDs from the data
                osd_count = len(data.get("nodes", []))
                
                # Enumerate OSD data directories
                for osd_id in range(osd_count):
                    osd_path = f"/var/snap/microceph/common/data/osd/ceph-{osd_id + 1}"
                    paths.append(osd_path)
            except (json.JSONDecodeError, KeyError):
                pass
        
        # If we couldn't get paths from ceph, try enumerating the directory
        if not paths:
            result = executor.run(
                host,
                ["ls", "-1", "/var/snap/microceph/common/data/osd/"],
                timeout=10,
                check=False,
            )
            
            if result.returncode == 0:
                for dirname in result.stdout.strip().split("\n"):
                    if dirname.startswith("ceph-"):
                        paths.append(f"/var/snap/microceph/common/data/osd/{dirname}")
    
    except Exception:
        pass
    
    return paths


def check_osd_disk_capacity(
    host: str,
    executor: RemoteExecutor | None = None,
    custom_paths: list[str] | None = None,
    threshold: int = 85,
) -> ProbeResult:
    """Check disk capacity for MicroCeph OSD data paths.
    
    Args:
        host: Target hostname
        executor: Remote executor instance
        custom_paths: Optional list of custom OSD paths to check
        threshold: Disk usage threshold percentage (default: 85, Ceph nearfull)
    """
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    # Get OSD paths
    if custom_paths:
        osd_paths = custom_paths
    else:
        osd_paths = get_microceph_osd_paths(host, executor)
    
    if not osd_paths:
        return ProbeResult(
            probe_name="OSD Disk Capacity",
            host=host,
            passed=True,
            message="No MicroCeph OSDs found on this host",
            details={"osd_count": 0},
        )
    
    try:
        # Check each OSD path
        osd_details: dict[str, Any] = {"osds": []}
        all_passed = True
        failed_osds = []
        
        for osd_path in osd_paths:
            result = executor.run(
                host,
                ["df", "-h", osd_path],
                timeout=10,
                check=False,
            )
            
            if result.returncode != 0:
                # Path doesn't exist or can't be accessed
                osd_details["osds"].append({
                    "path": osd_path,
                    "status": "inaccessible",
                })
                all_passed = False
                failed_osds.append(f"{osd_path} (inaccessible)")
                continue
            
            # Parse df output
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                fields = lines[1].split()
                if len(fields) >= 5:
                    use_pct = int(fields[4].rstrip("%"))
                    osd_info = {
                        "path": osd_path,
                        "filesystem": fields[0],
                        "size": fields[1],
                        "used": fields[2],
                        "available": fields[3],
                        "use_percent": fields[4],
                        "status": "ok" if use_pct < threshold else "full",
                    }
                    osd_details["osds"].append(osd_info)
                    
                    if use_pct >= threshold:
                        all_passed = False
                        failed_osds.append(f"{osd_path} ({use_pct}%)")
        
        osd_details["osd_count"] = len(osd_paths)
        osd_details["threshold"] = f"{threshold}%"
        
        if all_passed:
            message = f"All {len(osd_paths)} OSD(s) disk usage below {threshold}%"
        else:
            message = f"OSD disk usage threshold exceeded: {', '.join(failed_osds)}"
        
        return ProbeResult(
            probe_name="OSD Disk Capacity",
            host=host,
            passed=all_passed,
            message=message,
            details=osd_details,
        )
    
    except subprocess.TimeoutExpired:
        return ProbeResult(
            probe_name="OSD Disk Capacity",
            host=host,
            passed=False,
            message="Command timed out",
        )
    
    except Exception as e:
        return ProbeResult(
            probe_name="OSD Disk Capacity",
            host=host,
            passed=False,
            message=f"Unexpected error: {str(e)}",
        )


def check_host_resources(
    host: str,
    executor: RemoteExecutor | None = None,
    min_cpu_cores: int = 2,
    min_memory_gb: float = 2.0,
) -> ProbeResult:
    """Check host resource availability (CPU, memory).
    
    Args:
        host: Target hostname
        executor: Remote executor instance
        min_cpu_cores: Minimum required CPU cores (default: 2)
        min_memory_gb: Minimum required memory in GB (default: 2.0 for MicroCeph)
    """
    if executor is None:
        executor = RemoteExecutor(transport="lxd")
    
    try:
        # Check memory
        mem_result = executor.run(
            host,
            ["free", "-h"],
            timeout=10,
            check=True,
        )
        
        # Check CPU
        cpu_result = executor.run(
            host,
            ["nproc"],
            timeout=10,
            check=True,
        )
        
        details: dict[str, Any] = {}
        
        # Parse memory info
        mem_lines = mem_result.stdout.strip().split("\n")
        mem_total_gb = 0.0
        if len(mem_lines) >= 2:
            mem_fields = mem_lines[1].split()
            if len(mem_fields) >= 2:
                details["memory_total"] = mem_fields[1]
                details["memory_used"] = mem_fields[2] if len(mem_fields) > 2 else "N/A"
                details["memory_available"] = mem_fields[-1]
                
                # Parse total memory to GB for validation
                try:
                    mem_total_gb = parse_memory_to_gb(mem_fields[1])
                    details["memory_total_gb"] = f"{mem_total_gb:.2f}"
                except ValueError as e:
                    details["memory_parse_error"] = str(e)
        
        # Parse CPU info
        cpu_count = cpu_result.stdout.strip()
        details["cpu_cores"] = cpu_count
        
        # Validation with thresholds
        passed = True
        messages = []
        
        # Validate CPU
        try:
            cpu_int = int(cpu_count)
            if cpu_int < min_cpu_cores:
                passed = False
                messages.append(f"CPU: {cpu_int} cores (minimum: {min_cpu_cores})")
            else:
                messages.append(f"CPU: {cpu_int} cores (minimum: {min_cpu_cores}) ✓")
        except ValueError:
            passed = False
            messages.append("Could not parse CPU count")
        
        # Validate memory
        if mem_total_gb > 0:
            if mem_total_gb < min_memory_gb:
                passed = False
                messages.append(f"Memory: {mem_total_gb:.2f} GB (minimum: {min_memory_gb} GB)")
            else:
                messages.append(f"Memory: {mem_total_gb:.2f} GB (minimum: {min_memory_gb} GB) ✓")
        else:
            passed = False
            messages.append("Could not parse memory total")
        
        # Store thresholds in details
        details["min_cpu_cores"] = min_cpu_cores
        details["min_memory_gb"] = min_memory_gb
        
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
