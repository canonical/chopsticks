"""Unit tests for probe modules."""

from unittest.mock import MagicMock, patch
import subprocess

from chopsticks.probes.cluster_health import check_microceph_status, check_ceph_status
from chopsticks.probes.network import check_network_reachability
from chopsticks.probes.resources import check_disk_capacity, check_host_resources


@patch("chopsticks.probes.cluster_health.subprocess.run")
def test_check_microceph_status_success(mock_run):
    """Test successful microceph status check."""
    mock_run.return_value = MagicMock(
        stdout="MicroCeph deployment summary:\n- host1 (1.2.3.4)\n  Services: mon, mgr\n  Disks: 2",
        stderr="",
    )
    
    result = check_microceph_status("host1")
    
    assert result.passed is True
    assert result.host == "host1"
    assert "operational" in result.message.lower()


@patch("chopsticks.probes.cluster_health.subprocess.run")
def test_check_microceph_status_failure(mock_run):
    """Test failed microceph status check."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="Error: Command not found")
    
    result = check_microceph_status("host1")
    
    assert result.passed is False
    assert result.host == "host1"


@patch("chopsticks.probes.cluster_health.subprocess.run")
def test_check_ceph_status_health_ok(mock_run):
    """Test ceph status with HEALTH_OK."""
    mock_run.return_value = MagicMock(
        stdout="cluster:\n  health: HEALTH_OK\n  services:\n    mon: 1 daemon",
        stderr="",
    )
    
    result = check_ceph_status("host1")
    
    assert result.passed is True
    assert "HEALTH_OK" in result.message


@patch("chopsticks.probes.cluster_health.subprocess.run")
def test_check_ceph_status_health_warn(mock_run):
    """Test ceph status with HEALTH_WARN."""
    mock_run.return_value = MagicMock(
        stdout="cluster:\n  health: HEALTH_WARN\n  services:\n    mon: 1 daemon",
        stderr="",
    )
    
    result = check_ceph_status("host1")
    
    assert result.passed is False
    assert "HEALTH_WARN" in result.message


@patch("chopsticks.probes.network.subprocess.run")
def test_check_network_reachability_success(mock_run):
    """Test successful network reachability check."""
    mock_run.return_value = MagicMock(
        stdout="ping",
        stderr="",
        returncode=0,
    )
    
    result = check_network_reachability("host1")
    
    assert result.passed is True
    assert result.host == "host1"


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_disk_capacity_normal(mock_run):
    """Test disk capacity check with normal usage."""
    mock_run.return_value = MagicMock(
        stdout="Filesystem      Size  Used Avail Use%\n/dev/sda1       100G   30G   70G  30%",
        stderr="",
    )
    
    result = check_disk_capacity("host1")
    
    assert result.passed is True
    assert result.host == "host1"


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_disk_capacity_high_usage(mock_run):
    """Test disk capacity check with high usage."""
    mock_run.return_value = MagicMock(
        stdout="Filesystem      Size  Used Avail Use%\n/dev/sda1       100G   95G    5G  95%",
        stderr="",
    )
    
    result = check_disk_capacity("host1")
    
    assert result.passed is False
    assert "high" in result.message.lower()


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_adequate(mock_run):
    """Test host resources check with adequate resources."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           16Gi        8Gi        8Gi")
        elif "nproc" in cmd:
            return MagicMock(stdout="4")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1")
    
    assert result.passed is True
    assert result.host == "host1"


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_low_cpu(mock_run):
    """Test host resources check with low CPU count."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           16Gi        8Gi        8Gi")
        elif "nproc" in cmd:
            return MagicMock(stdout="1")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1")
    
    assert result.passed is False
    assert "cpu" in result.message.lower()
