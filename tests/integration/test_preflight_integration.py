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


def hosts_available() -> bool:
    """Check if test hosts exist."""
    if not lxd_available():
        return False
    try:
        result = subprocess.run(
            ["lxc", "list", "--format", "json"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        hosts = json.loads(result.stdout)
        host_names = {h["name"] for h in hosts}
        return "storage-01" in host_names or "client-01" in host_names
    except Exception:
        return False


# Dynamic project root for portable tests (Fix Finding #2)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
def test_preflight_storage_01():
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
def test_preflight_client_01():
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
def test_preflight_multiple_hosts():
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
