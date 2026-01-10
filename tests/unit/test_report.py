"""Unit tests for report utilities."""

from chopsticks.utils.report import ProbeResult, PreflightReport


def test_probe_result_creation():
    """Test creating a ProbeResult."""
    result = ProbeResult(
        probe_name="Test Probe",
        host="test-host",
        passed=True,
        message="Test message",
        details={"key": "value"},
    )
    
    assert result.probe_name == "Test Probe"
    assert result.host == "test-host"
    assert result.passed is True
    assert result.message == "Test message"
    assert result.details == {"key": "value"}


def test_preflight_report_all_passed():
    """Test all_passed method."""
    report = PreflightReport()
    
    report.add_result(ProbeResult(probe_name="Test1", host="host1", passed=True))
    report.add_result(ProbeResult(probe_name="Test2", host="host1", passed=True))
    
    assert report.all_passed() is True


def test_preflight_report_with_failures():
    """Test all_passed with failures."""
    report = PreflightReport()
    
    report.add_result(ProbeResult(probe_name="Test1", host="host1", passed=True))
    report.add_result(ProbeResult(probe_name="Test2", host="host1", passed=False))
    
    assert report.all_passed() is False


def test_preflight_report_summary():
    """Test get_summary method."""
    report = PreflightReport()
    
    report.add_result(ProbeResult(probe_name="Test1", host="host1", passed=True))
    report.add_result(ProbeResult(probe_name="Test2", host="host1", passed=False))
    report.add_result(ProbeResult(probe_name="Test3", host="host2", passed=True))
    
    summary = report.get_summary()
    
    assert summary["host1"]["total"] == 2
    assert summary["host1"]["passed"] == 1
    assert summary["host1"]["failed"] == 1
    
    assert summary["host2"]["total"] == 1
    assert summary["host2"]["passed"] == 1
    assert summary["host2"]["failed"] == 0
