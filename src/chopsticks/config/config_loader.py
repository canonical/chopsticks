"""Configuration loader for Chopsticks."""

from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigLoader:
    """Load and validate configuration files."""
    
    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        self._validate_config(config)
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If configuration is invalid
        """
        if "workload" not in config:
            raise ValueError("Configuration must contain 'workload' section")
        
        workload = config["workload"]
        if "type" not in workload:
            raise ValueError("Workload must specify 'type'")
        
        workload_type = workload["type"]
        
        if workload_type == "s3":
            if "s3" not in config:
                raise ValueError("S3 workload requires 's3' configuration section")
            
            s3_config = config["s3"]
            required_fields = ["endpoint", "access_key", "secret_key", "region"]
            for field in required_fields:
                if field not in s3_config:
                    raise ValueError(f"S3 configuration missing required field: {field}")
