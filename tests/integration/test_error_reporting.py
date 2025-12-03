"""
Integration test to verify error reporting in Locust

This test creates a bad configuration and runs a Locust test
to ensure failures are properly reported.
"""

import tempfile
import os
import yaml
import subprocess
import pytest


@pytest.mark.integration
@pytest.mark.timeout(30)
def test_locust_reports_failures_with_bad_config():
    """Test that Locust properly reports failures when given invalid configuration"""

    # Create a temporary config file with invalid credentials
    bad_config = {
        "endpoint": "http://invalid-endpoint-that-does-not-exist:9999",
        "access_key": "invalid_access_key",
        "secret_key": "invalid_secret_key",
        "region": "default",
        "bucket": "invalid-bucket",
        "driver": "s5cmd",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(bad_config, f)
        config_path = f.name

    try:
        # Run chopsticks CLI in headless mode for a short time
        cmd = [
            "uv",
            "run",
            "chopsticks",
            "--workload-config",
            config_path,
            "-f",
            "src/chopsticks/scenarios/s3_large_objects.py",
            "--headless",
            "--users",
            "2",
            "--spawn-rate",
            "2",
            "--duration",
            "10s",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Check that the output contains failure information
        # Locust should report failures
        assert (
            "100% failures" in output or "Failures/s" in output or "# fails" in output
        ), f"Expected failure reporting in output, got:\n{output}"

        # The test should complete (not hang forever)
        assert result.returncode in [0, 1], (
            f"Unexpected return code: {result.returncode}"
        )

    finally:
        # Clean up temp file
        if os.path.exists(config_path):
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
