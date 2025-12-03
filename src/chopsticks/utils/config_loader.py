import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_config_path(workload: str, config_name: str | None = None) -> Path:
    """
    Get configuration file path

    Args:
        workload: Workload name (e.g., 's3', 'rbd')
        config_name: Optional config name, defaults to <workload>_config.yaml

    Returns:
        Path to configuration file
    """
    if config_name is None:
        config_name = f"{workload}_config.yaml"

    # Try multiple paths
    paths = [
        Path.cwd() / "config" / config_name,
        Path(__file__).parent.parent / "config" / config_name,
        Path.home() / ".chopsticks" / config_name,
    ]

    for path in paths:
        if path.exists():
            return path

    # Return default path (will fail later if not exists)
    return paths[0]
