"""Integration tests for pre-flight checks."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


# Helper functions for skip guards
def lxd_available() -> bool:
    """Check if LXD is available."""
    return shutil.which("lxc") is not None


def uv_available() -> bool:
    """Check if uv is available."""
    return shutil.which("uv") is not None


def host_exists(hostname: str) -> bool:
    """Check if a specific LXD host exists."""
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
        return len(hosts) > 0 and hosts[0].get("name") == hostname
    except Exception:
        return False


def hosts_available() -> bool:
    """Check if test hosts exist."""
    return host_exists("storage-01") or host_exists("client-01")


# Dynamic project root for portable tests (Fix Finding #2)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def integration_env():
    """Validate integration test environment with actionable error messages.
    
    This fixture checks for all required dependencies and provides clear
    installation instructions if anything is missing.
    """
    missing = []
    
    if not lxd_available():
        missing.append("LXD - Install: snap install lxd && lxd init --auto")
    
    if not uv_available():
        missing.append("uv - Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
    
    # Check for specific required hosts
    required_hosts = ["storage-01", "client-01"]
    for hostname in required_hosts:
        if not host_exists(hostname):
            missing.append(
                f"LXD VM '{hostname}' - See tests/integration/README.md for setup"
            )
    
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
@pytest.mark.skipif(not lxd_available(), reason="LXD not available")
@pytest.mark.skipif(not uv_available(), reason="uv not installed")
@pytest.mark.skipif(not hosts_available(), reason="Test VMs not running")
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
@pytest.mark.skipif(not lxd_available(), reason="LXD not available")
@pytest.mark.skipif(not uv_available(), reason="uv not installed")
@pytest.mark.skipif(not hosts_available(), reason="Test VMs not running")
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
    assert "Command not found" in result.stdout


@pytest.mark.integration
@pytest.mark.skipif(not lxd_available(), reason="LXD not available")
@pytest.mark.skipif(not uv_available(), reason="uv not installed")
@pytest.mark.skipif(not hosts_available(), reason="Test VMs not running")
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
