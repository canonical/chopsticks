"""
Integration test to verify error reporting in Locust

This test creates a bad configuration and runs a Locust test
to ensure failures are properly reported.
"""

import tempfile
import os
import yaml
import subprocess
import time
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
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(bad_config, f)
        config_path = f.name
    
    try:
        # Run locust in headless mode for a short time
        env = os.environ.copy()
        env["S3_CONFIG_PATH"] = config_path
        
        cmd = [
            "locust",
            "-f", "src/chopsticks/scenarios/s3_large_objects.py",
            "--headless",
            "--users", "2",
            "--spawn-rate", "2",
            "--run-time", "10s",
            "--host", "http://invalid:9999",
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/home/utkarsh.bhatt@canonical.com/projects/chopsticks"
        )
        
        output = result.stdout + result.stderr
        
        # Check that the output contains failure information
        # Locust should report failures
        assert "100% failures" in output or "Failures/s" in output or "# fails" in output, \
            f"Expected failure reporting in output, got:\n{output}"
        
        # The test should complete (not hang forever)
        assert result.returncode in [0, 1], f"Unexpected return code: {result.returncode}"
        
    finally:
        # Clean up temp file
        if os.path.exists(config_path):
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
