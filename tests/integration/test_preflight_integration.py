"""Integration tests for pre-flight checks.

All integration tests use the integration_env fixture as the single validation point.
The fixture checks for LXD, uv, and required VMs at runtime, providing actionable
error messages if any dependency is missing.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


# Helper functions used by integration_env fixture
def lxd_available() -> bool:
    """Check if LXD is available."""
    return shutil.which("lxc") is not None


def uv_available() -> bool:
    """Check if uv is available."""
    return shutil.which("uv") is not None


def get_vm_status(hostname: str) -> str:
    """Get detailed VM status (running, stopped, frozen, not_found).
    
    Returns:
        "running" - VM exists and is running
        "stopped" - VM exists but is stopped/shutdown
        "frozen" - VM exists but is frozen
        "not_found" - VM does not exist
        "unknown" - Unable to determine status
    """
    if not lxd_available():
        return "not_found"
    
    try:
        result = subprocess.run(
            ["lxc", "list", hostname, "--format", "json"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "not_found"
        
        hosts = json.loads(result.stdout)
        if not hosts:
            return "not_found"
        
        state = hosts[0].get("state", {})
        status = state.get("status", "unknown").lower()
        return status
    except Exception:
        return "unknown"


def host_exists(hostname: str) -> bool:
    """Check if a specific LXD host exists and is running.
    
    Returns True only if VM exists AND is in Running state.
    """
    if not lxd_available():
        return False
    try:
        result = subprocess.run(
            ["lxc", "list", hostname, "--format", "json"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        hosts = json.loads(result.stdout)
        if not hosts or hosts[0].get("name") != hostname:
            return False
        
        # Check if VM is running
        state = hosts[0].get("state", {})
        status = state.get("status", "").upper()
        
        # Require Running state
        return status == "RUNNING"
    except Exception:
        return False


# Dynamic project root for portable tests (Fix Finding #2)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def integration_env():
    """Validate integration test environment with state-aware error messages.
    
    This is the single validation point for all integration tests. It checks:
    - LXD availability
    - uv availability  
    - Required VMs exist AND are running
    
    Provides actionable error messages with specific remediation steps.
    """
    missing = []
    
    if not lxd_available():
        missing.append("LXD - Install: snap install lxd && lxd init --auto")
    
    if not uv_available():
        missing.append("uv - Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
    
    # Check for specific required hosts with state awareness
    required_hosts = ["storage-01", "client-01"]
    for hostname in required_hosts:
        if not host_exists(hostname):
            # Provide detailed reason based on VM state
            status = get_vm_status(hostname)
            if status == "stopped":
                missing.append(f"VM '{hostname}' is stopped - Start: lxc start {hostname}")
            elif status == "frozen":
                missing.append(f"VM '{hostname}' is frozen - Resume: lxc start {hostname}")
            elif status == "not_found":
                missing.append(f"VM '{hostname}' not found - See tests/integration/README.md")
            else:
                missing.append(f"VM '{hostname}' in unexpected state: {status}")
    
    if missing:
        skip_msg = "Missing integration test dependencies:\n  - " + "\n  - ".join(missing)
        pytest.skip(skip_msg)


def test_preflight_cli_help():
    """Test that the preflight CLI help works."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--help"],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    assert "Run pre-flight checks" in result.stdout


def test_preflight_requires_host():
    """Test that preflight requires --host argument."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight"],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode != 0
    assert "required" in result.stderr.lower() or "missing" in result.stderr.lower()


@pytest.mark.integration
def test_preflight_storage_01(integration_env):
    """Test preflight against storage-01 (requires LXD VM to be running)."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "storage-01"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    
    # Should pass for storage-01 which has MicroCeph
    assert result.returncode == 0
    assert "All pre-flight checks passed" in result.stdout
    assert "MicroCeph Status" in result.stdout
    assert "Ceph Status" in result.stdout


@pytest.mark.integration
def test_preflight_client_01(integration_env):
    """Test preflight against client-01 (requires LXD VM to be running)."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "client-01"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    
    # Should fail for client-01 which doesn't have MicroCeph
    assert result.returncode != 0
    assert "Pre-flight checks failed" in result.stdout
    assert "command not found" in result.stdout  # Updated for sudo wrapper output


@pytest.mark.integration
def test_preflight_multiple_hosts(integration_env):
    """Test preflight against multiple hosts."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "storage-01", "--host", "client-01"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    
    # Should fail due to client-01
    assert result.returncode != 0
    assert "storage-01" in result.stdout
    assert "client-01" in result.stdout
