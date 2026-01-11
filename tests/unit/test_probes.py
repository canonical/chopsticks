"""Unit tests for probe modules."""

from unittest.mock import MagicMock, patch
import subprocess

from chopsticks.probes.cluster_health import check_microceph_status, check_ceph_status
from chopsticks.probes.network import check_network_reachability
from chopsticks.probes.resources import (
    check_root_disk_capacity,
    check_osd_disk_capacity,
    check_host_resources,
    get_microceph_osd_paths,
    parse_memory_to_gb,
)
from chopsticks.utils.report import ProbeResult
import pytest


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


@patch("chopsticks.probes.network.RemoteExecutor")
def test_check_network_reachability_success(mock_executor_class):
    """Test successful network reachability check."""
    mock_executor = MagicMock()
    mock_executor_class.return_value = mock_executor
    
    # Mock successful connectivity test
    mock_executor.test_connectivity.return_value = ProbeResult(
        probe_name="Network Reachability",
        host="host1",
        passed=True,
        message="Host reachable",
        details={"method": "lxd"},
    )
    
    result = check_network_reachability("host1")
    
    assert result.passed is True
    assert result.host == "host1"


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_root_disk_capacity_normal(mock_run):
    """Test root disk capacity check with normal usage."""
    mock_run.return_value = MagicMock(
        stdout="Filesystem      Size  Used Avail Use%\n/dev/sda1       100G   30G   70G  30%",
        stderr="",
    )
    
    result = check_root_disk_capacity("host1")
    
    assert result.passed is True
    assert result.host == "host1"
    assert "Root" in result.probe_name


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_root_disk_capacity_high_usage(mock_run):
    """Test root disk capacity check with high usage."""
    mock_run.return_value = MagicMock(
        stdout="Filesystem      Size  Used Avail Use%\n/dev/sda1       100G   95G    5G  95%",
        stderr="",
    )
    
    result = check_root_disk_capacity("host1")
    
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


def test_get_microceph_osd_paths_with_ceph_data():
    """Test OSD path discovery from ceph osd df command."""
    mock_executor = MagicMock()
    mock_executor.run.return_value = MagicMock(
        returncode=0,
        stdout='{"nodes": [{"id": 1}, {"id": 2}, {"id": 3}]}',
    )
    
    paths = get_microceph_osd_paths("host1", mock_executor)
    
    assert len(paths) == 3
    assert "/var/snap/microceph/common/data/osd/ceph-1" in paths
    assert "/var/snap/microceph/common/data/osd/ceph-2" in paths
    assert "/var/snap/microceph/common/data/osd/ceph-3" in paths


def test_get_microceph_osd_paths_with_ls_fallback():
    """Test OSD path discovery via directory enumeration fallback."""
    mock_executor = MagicMock()
    
    def mock_run(host, cmd, **kwargs):
        if "ceph" in cmd:
            return MagicMock(returncode=1, stdout="")
        elif "ls" in cmd:
            return MagicMock(returncode=0, stdout="ceph-1\nceph-2\n")
        return MagicMock(returncode=1, stdout="")
    
    mock_executor.run.side_effect = mock_run
    
    paths = get_microceph_osd_paths("host1", mock_executor)
    
    assert len(paths) == 2
    assert "/var/snap/microceph/common/data/osd/ceph-1" in paths
    assert "/var/snap/microceph/common/data/osd/ceph-2" in paths


def test_check_osd_disk_capacity_no_osds():
    """Test OSD disk check when no OSDs found."""
    mock_executor = MagicMock()
    mock_executor.run.return_value = MagicMock(returncode=1, stdout="")
    
    result = check_osd_disk_capacity("host1", mock_executor)
    
    assert result.passed is True
    assert "No MicroCeph OSDs found" in result.message
    assert result.details["osd_count"] == 0


def test_check_osd_disk_capacity_all_healthy():
    """Test OSD disk check with all OSDs below threshold."""
    mock_executor = MagicMock()
    
    # Mock get_microceph_osd_paths to return test paths
    test_paths = [
        "/var/snap/microceph/common/data/osd/ceph-1",
        "/var/snap/microceph/common/data/osd/ceph-2",
    ]
    
    with patch("chopsticks.probes.resources.get_microceph_osd_paths", return_value=test_paths):
        mock_executor.run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem      Size  Used Avail Use%\n/dev/sdb1       100G   50G   50G  50%",
        )
        
        result = check_osd_disk_capacity("host1", mock_executor, threshold=85)
        
        assert result.passed is True
        assert "All 2 OSD(s)" in result.message
        assert result.details["osd_count"] == 2


def test_check_osd_disk_capacity_threshold_exceeded():
    """Test OSD disk check with OSD exceeding threshold."""
    mock_executor = MagicMock()
    
    test_paths = ["/var/snap/microceph/common/data/osd/ceph-1"]
    
    with patch("chopsticks.probes.resources.get_microceph_osd_paths", return_value=test_paths):
        mock_executor.run.return_value = MagicMock(
            returncode=0,
            stdout="Filesystem      Size  Used Avail Use%\n/dev/sdb1       100G   90G   10G  90%",
        )
        
        result = check_osd_disk_capacity("host1", mock_executor, threshold=85)
        
        assert result.passed is False
        assert "threshold exceeded" in result.message
        assert "90%" in result.message


def test_check_osd_disk_capacity_custom_paths():
    """Test OSD disk check with custom paths."""
    mock_executor = MagicMock()
    mock_executor.run.return_value = MagicMock(
        returncode=0,
        stdout="Filesystem      Size  Used Avail Use%\n/dev/sdc1       100G   30G   70G  30%",
    )
    
    custom_paths = ["/custom/osd/path"]
    result = check_osd_disk_capacity("host1", mock_executor, custom_paths=custom_paths)
    
    assert result.passed is True
    assert result.details["osd_count"] == 1

# Memory Parsing Tests
def test_parse_memory_to_gb_bytes():
    """Test parsing bytes to GB."""
    assert parse_memory_to_gb("1073741824") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("2147483648B") == pytest.approx(2.0, rel=1e-2)


def test_parse_memory_to_gb_kilobytes():
    """Test parsing kilobytes to GB."""
    assert parse_memory_to_gb("1048576K") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1048576KB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1048576KiB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("2097152Ki") == pytest.approx(2.0, rel=1e-2)


def test_parse_memory_to_gb_megabytes():
    """Test parsing megabytes to GB."""
    assert parse_memory_to_gb("1024M") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1024MB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1024MiB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("2048Mi") == pytest.approx(2.0, rel=1e-2)
    assert parse_memory_to_gb("512Mi") == pytest.approx(0.5, rel=1e-2)


def test_parse_memory_to_gb_gigabytes():
    """Test parsing gigabytes to GB."""
    assert parse_memory_to_gb("1G") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1GB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("1GiB") == pytest.approx(1.0, rel=1e-2)
    assert parse_memory_to_gb("16Gi") == pytest.approx(16.0, rel=1e-2)
    assert parse_memory_to_gb("2.5GB") == pytest.approx(2.5, rel=1e-2)


def test_parse_memory_to_gb_terabytes():
    """Test parsing terabytes to GB."""
    assert parse_memory_to_gb("1T") == pytest.approx(1024.0, rel=1e-2)
    assert parse_memory_to_gb("1TB") == pytest.approx(1024.0, rel=1e-2)
    assert parse_memory_to_gb("1TiB") == pytest.approx(1024.0, rel=1e-2)
    assert parse_memory_to_gb("2Ti") == pytest.approx(2048.0, rel=1e-2)


def test_parse_memory_to_gb_with_spaces():
    """Test parsing memory values with spaces."""
    assert parse_memory_to_gb("16 Gi") == pytest.approx(16.0, rel=1e-2)
    assert parse_memory_to_gb("2048 Mi") == pytest.approx(2.0, rel=1e-2)
    assert parse_memory_to_gb("512 MB") == pytest.approx(0.5, rel=1e-2)


def test_parse_memory_to_gb_case_insensitive():
    """Test parsing memory values is case insensitive."""
    assert parse_memory_to_gb("16gi") == pytest.approx(16.0, rel=1e-2)
    assert parse_memory_to_gb("16GI") == pytest.approx(16.0, rel=1e-2)
    assert parse_memory_to_gb("16Gi") == pytest.approx(16.0, rel=1e-2)


def test_parse_memory_to_gb_invalid_format():
    """Test parsing invalid memory format raises ValueError."""
    with pytest.raises(ValueError):
        parse_memory_to_gb("invalid")
    with pytest.raises(ValueError):
        parse_memory_to_gb("16 invalid")
    with pytest.raises(ValueError):
        parse_memory_to_gb("")


def test_parse_memory_to_gb_unknown_unit():
    """Test parsing unknown unit raises ValueError."""
    with pytest.raises(ValueError):
        parse_memory_to_gb("16XB")
    with pytest.raises(ValueError):
        parse_memory_to_gb("16ZZ")


# Memory Validation Tests
@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_memory_sufficient(mock_run):
    """Test host resources check with sufficient memory."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           4Gi        2Gi        2Gi")
        elif "nproc" in cmd:
            return MagicMock(stdout="4")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1", min_cpu_cores=2, min_memory_gb=2.0)
    
    assert result.passed is True
    assert result.host == "host1"
    assert "4.00 GB" in result.message or "4 GB" in result.message
    assert "✓" in result.message


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_memory_insufficient(mock_run):
    """Test host resources check with insufficient memory."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           512Mi      256Mi      256Mi")
        elif "nproc" in cmd:
            return MagicMock(stdout="4")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1", min_cpu_cores=2, min_memory_gb=2.0)
    
    assert result.passed is False
    assert "Memory:" in result.message
    assert "minimum: 2" in result.message.lower() or "minimum: 2.0" in result.message.lower()


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_cpu_and_memory_insufficient(mock_run):
    """Test host resources check with both CPU and memory insufficient."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           1Gi        512Mi      512Mi")
        elif "nproc" in cmd:
            return MagicMock(stdout="1")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1", min_cpu_cores=2, min_memory_gb=2.0)
    
    assert result.passed is False
    assert "CPU:" in result.message
    assert "Memory:" in result.message


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_custom_thresholds(mock_run):
    """Test host resources check with custom thresholds."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           8Gi        4Gi        4Gi")
        elif "nproc" in cmd:
            return MagicMock(stdout="8")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    # Should pass with 4 CPU / 4GB thresholds
    result = check_host_resources("host1", min_cpu_cores=4, min_memory_gb=4.0)
    assert result.passed is True
    
    # Should fail with 16 CPU / 16GB thresholds
    result = check_host_resources("host1", min_cpu_cores=16, min_memory_gb=16.0)
    assert result.passed is False


@patch("chopsticks.probes.resources.subprocess.run")
def test_check_host_resources_memory_parse_error(mock_run):
    """Test host resources check handles memory parse errors."""
    def mock_subprocess_run(cmd, *args, **kwargs):
        if "free" in cmd:
            return MagicMock(stdout="              total        used        free\nMem:           INVALID    8Gi        8Gi")
        elif "nproc" in cmd:
            return MagicMock(stdout="4")
        return MagicMock(stdout="")
    
    mock_run.side_effect = mock_subprocess_run
    
    result = check_host_resources("host1", min_cpu_cores=2, min_memory_gb=2.0)
    
    assert result.passed is False
    assert "Could not parse memory" in result.message or "memory" in result.message.lower()