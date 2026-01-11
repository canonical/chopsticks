"""SSH and remote execution utilities."""

import socket
import subprocess
from typing import Any

from chopsticks.utils.report import ProbeResult


class RemoteExecutor:
    """Execute commands on remote hosts via SSH or LXD."""
    
    def __init__(self, transport: str = "ssh", user: str = "ubuntu"):
        """Initialize remote executor.
        
        Args:
            transport: Transport method - "ssh" or "lxd"
            user: SSH username (ignored for LXD transport)
        """
        if transport not in ("ssh", "lxd"):
            raise ValueError(f"Invalid transport: {transport}. Must be 'ssh' or 'lxd'")
        self.transport = transport
        self.user = user
    
    def run(
        self,
        host: str,
        command: list[str],
        timeout: int = 30,
        check: bool = True,
        use_sudo: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command on remote host.
        
        Args:
            host: Hostname or IP address
            command: Command to execute as list of strings
            timeout: Command timeout in seconds
            check: Whether to raise exception on non-zero exit
            use_sudo: Whether to wrap command with 'sudo -n' (non-interactive)
            
        Returns:
            CompletedProcess with stdout, stderr, and return code
        """
        # Wrap command with sudo if requested
        if use_sudo:
            command = ["sudo", "-n"] + command
        
        if self.transport == "ssh":
            return self._run_ssh(host, command, timeout, check)
        else:  # lxd
            return self._run_lxd(host, command, timeout, check)
    
    def _run_ssh(
        self,
        host: str,
        command: list[str],
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command via SSH."""
        ssh_command = [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            f"{self.user}@{host}",
        ] + command
        
        return subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
    
    def _run_lxd(
        self,
        host: str,
        command: list[str],
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Execute command via LXD exec."""
        lxd_command = ["lxc", "exec", host, "--"] + command
        
        return subprocess.run(
            lxd_command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )
    
    def test_connectivity(self, host: str) -> ProbeResult:
        """Test network connectivity to host.
        
        For SSH: Tests TCP connection and SSH handshake
        For LXD: Pings the VM's IP address
        
        Args:
            host: Hostname or IP address
            
        Returns:
            ProbeResult indicating success or failure
        """
        if self.transport == "ssh":
            return self._test_ssh_connectivity(host)
        else:  # lxd
            return self._test_lxd_connectivity(host)
    
    def _test_ssh_connectivity(self, host: str, port: int = 22) -> ProbeResult:
        """Test SSH connectivity (Fix Finding #4)."""
        details: dict[str, Any] = {"method": "ssh", "port": port}
        
        try:
            # First, test TCP connectivity
            sock = socket.create_connection((host, port), timeout=10)
            sock.close()
            details["tcp_connection"] = "success"
            
            # Then test SSH handshake with echo command
            result = subprocess.run(
                [
                    "ssh",
                    "-o", "ConnectTimeout=10",
                    "-o", "BatchMode=yes",
                    "-o", "StrictHostKeyChecking=no",
                    f"{self.user}@{host}",
                    "echo", "reachable",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            
            # Check for marker in output (tolerates MOTD and banner text)
            if result.returncode == 0 and "reachable" in result.stdout:
                details["ssh_handshake"] = "success"
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=True,
                    message=f"Host reachable via SSH at {host}:{port}",
                    details=details,
                )
            else:
                details["ssh_handshake"] = "failed"
                details["error"] = result.stderr.strip() if result.stderr else "No error output"
                if result.stdout:
                    details["stdout_sample"] = result.stdout[:200]
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=False,
                    message=f"SSH handshake failed: {result.stderr.strip()}",
                    details=details,
                )
                
        except socket.timeout:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message=f"Connection timeout to {host}:{port}",
                details=details,
            )
        except (socket.error, ConnectionRefusedError) as e:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message=f"Network unreachable: {str(e)}",
                details=details,
            )
        except subprocess.TimeoutExpired:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message="SSH command timed out",
                details=details,
            )
        except Exception as e:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message=f"Unexpected error: {str(e)}",
                details=details,
            )
    
    def _test_lxd_connectivity(self, host: str) -> ProbeResult:
        """Test LXD VM connectivity via ping to actual IP (Fix Finding #4)."""
        details: dict[str, Any] = {"method": "lxd"}
        
        try:
            # Get VM IP address
            ip_result = subprocess.run(
                ["lxc", "list", host, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if ip_result.returncode != 0:
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=False,
                    message=f"Failed to query LXD: {ip_result.stderr}",
                    details=details,
                )
            
            import json
            data = json.loads(ip_result.stdout)
            if not data or len(data) == 0:
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=False,
                    message=f"LXD VM {host} not found",
                    details=details,
                )
            
            # Extract IP address
            state = data[0].get("state", {})
            network = state.get("network", {})
            ip_addr = None
            
            for iface, info in network.items():
                if iface != "lo" and info.get("addresses"):
                    for addr in info["addresses"]:
                        if addr.get("family") == "inet":
                            ip_addr = addr.get("address")
                            break
                if ip_addr:
                    break
            
            if not ip_addr:
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=False,
                    message=f"Could not determine IP address for {host}",
                    details=details,
                )
            
            details["ip_address"] = ip_addr
            
            # Ping the actual IP address (not lxc exec)
            ping_result = subprocess.run(
                ["ping", "-c", "3", "-W", "5", ip_addr],
                capture_output=True,
                text=True,
                timeout=20,
            )
            
            if ping_result.returncode == 0:
                details["ping_status"] = "success"
                details["packet_loss"] = "0%"
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=True,
                    message=f"Host reachable at {ip_addr} (ICMP)",
                    details=details,
                )
            else:
                details["ping_status"] = "failed"
                return ProbeResult(
                    probe_name="Network Reachability",
                    host=host,
                    passed=False,
                    message=f"Ping failed to {ip_addr}",
                    details=details,
                )
                
        except subprocess.TimeoutExpired:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message="Network probe timed out",
                details=details,
            )
        except Exception as e:
            return ProbeResult(
                probe_name="Network Reachability",
                host=host,
                passed=False,
                message=f"Unexpected error: {str(e)}",
                details=details,
            )
