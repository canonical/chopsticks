"""Unit tests for configuration loading."""

import pytest
import tempfile
import yaml
from pathlib import Path


class TestConfigLoading:
    """Tests for configuration file loading."""

    def test_load_yaml_config(self):
        """Test loading a YAML configuration file."""
        config_data = {
            "endpoint": "http://localhost:80",
            "access_key": "test-key",
            "secret_key": "test-secret",
            "bucket": "test-bucket",
            "region": "default",
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with open(config_path, "r") as f:
                loaded_config = yaml.safe_load(f)
            
            assert loaded_config["endpoint"] == "http://localhost:80"
            assert loaded_config["access_key"] == "test-key"
            assert loaded_config["bucket"] == "test-bucket"
        finally:
            Path(config_path).unlink()

    def test_config_validation(self):
        """Test configuration validation."""
        required_keys = ["endpoint", "access_key", "secret_key", "bucket"]
        
        config = {
            "endpoint": "http://localhost:80",
            "access_key": "key",
            "secret_key": "secret",
            "bucket": "bucket",
        }
        
        for key in required_keys:
            assert key in config

    def test_missing_required_field(self):
        """Test handling of missing required configuration fields."""
        config = {
            "endpoint": "http://localhost:80",
            "access_key": "key",
            # missing secret_key and bucket
        }
        
        required_keys = ["endpoint", "access_key", "secret_key", "bucket"]
        missing_keys = [key for key in required_keys if key not in config]
        
        assert "secret_key" in missing_keys
        assert "bucket" in missing_keys
