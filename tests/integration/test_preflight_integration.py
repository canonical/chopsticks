"""Integration tests for pre-flight checks."""

import subprocess
import pytest


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
def test_preflight_storage_01():
    """Test preflight against storage-01 (requires LXD VM to be running)."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "storage-01"],
        capture_output=True,
        text=True,
        cwd="/home/utkarsh.bhatt@canonical.com/projects/chopsticks",
    )
    
    # Should pass for storage-01 which has MicroCeph
    assert result.returncode == 0
    assert "All pre-flight checks passed" in result.stdout
    assert "MicroCeph Status" in result.stdout
    assert "Ceph Status" in result.stdout


@pytest.mark.integration
def test_preflight_client_01():
    """Test preflight against client-01 (requires LXD VM to be running)."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "client-01"],
        capture_output=True,
        text=True,
        cwd="/home/utkarsh.bhatt@canonical.com/projects/chopsticks",
    )
    
    # Should fail for client-01 which doesn't have MicroCeph
    assert result.returncode != 0
    assert "Pre-flight checks failed" in result.stdout
    assert "Command not found" in result.stdout


@pytest.mark.integration
def test_preflight_multiple_hosts():
    """Test preflight against multiple hosts."""
    result = subprocess.run(
        ["uv", "run", "chopsticks", "preflight", "--host", "storage-01", "--host", "client-01"],
        capture_output=True,
        text=True,
        cwd="/home/utkarsh.bhatt@canonical.com/projects/chopsticks",
    )
    
    # Should fail due to client-01
    assert result.returncode != 0
    assert "storage-01" in result.stdout
    assert "client-01" in result.stdout
