# Chopsticks - Ceph Stress Testing Framework

A flexible, extensible stress testing framework for Ceph storage using Locust to drive parallel workers and simulate real-world traffic patterns.

## Features

- **Extensible Workload Architecture**: Currently supports S3, designed to easily add RBD and other workloads
- **Multiple Client Drivers**: Pluggable driver system (currently uses s5cmd for S3)
- **Scenario-Based Testing**: Define and run various stress test scenarios
- **Locust-Powered**: Leverage Locust for distributed load generation
- **Configuration-Driven**: YAML-based configuration for workloads and scenarios

## Architecture

```
chopsticks/
├── workloads/          # Workload implementations (S3, RBD, etc.)
│   ├── s3/            # S3 workload
│   └── rbd/           # RBD workload (future)
├── drivers/            # Client driver implementations
│   ├── s3/            # S3 drivers (s5cmd, boto3, etc.)
│   └── rbd/           # RBD drivers (future)
├── scenarios/          # Test scenario definitions
├── config/             # Configuration files
└── utils/              # Utility functions
```

## Quick Start

### Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### Download s5cmd (S3 driver)

```bash
./scripts/install_s5cmd.sh
```

### Configure S3 Endpoint

Edit `config/s3_config.yaml`:

```yaml
endpoint: https://s3.example.com
access_key: YOUR_ACCESS_KEY
secret_key: YOUR_SECRET_KEY
bucket: test-bucket
region: us-east-1
driver: s5cmd
```

### Run a Test

```bash
# Run large object test with web UI (default: http://localhost:8089)
uv run locust -f chopsticks/scenarios/s3_large_objects.py

# Run headless mode with 10 users, spawn rate 2/sec, run for 10 minutes
uv run locust -f chopsticks/scenarios/s3_large_objects.py --headless -u 10 -r 2 -t 10m

# Run distributed (master)
uv run locust -f chopsticks/scenarios/s3_large_objects.py --master

# Run distributed (worker)
uv run locust -f chopsticks/scenarios/s3_large_objects.py --worker --master-host=<master-ip>
```

## Creating New Scenarios

1. Create a new scenario file in `chopsticks/scenarios/`
2. Inherit from the appropriate workload class
3. Define your test tasks with `@task` decorator

Example:

```python
from locust import task
from chopsticks.workloads.s3.s3_workload import S3Workload

class MyCustomScenario(S3Workload):
    @task
    def custom_test(self):
        # Your test logic here
        self.upload_object("test-key", "test-data")
```

## Available Scenarios

### S3 Large Objects
Tests upload and download of large objects (configurable size, default 100MB).

```bash
uv run locust -f chopsticks/scenarios/s3_large_objects.py
```

## Adding New Drivers

1. Create driver class in `chopsticks/drivers/s3/` (or appropriate workload)
2. Implement the `BaseS3Driver` interface
3. Update workload configuration to use new driver

Example:

```python
from chopsticks.drivers.s3.base import BaseS3Driver

class MyS3Driver(BaseS3Driver):
    def upload(self, key: str, data: bytes) -> bool:
        # Implementation
        pass
    
    def download(self, key: str) -> bytes:
        # Implementation
        pass
```

## Extending to RBD

The framework is designed for easy extension. To add RBD support:

1. Create `chopsticks/workloads/rbd/rbd_workload.py`
2. Create driver in `chopsticks/drivers/rbd/`
3. Define RBD configuration in `config/rbd_config.yaml`
4. Create scenarios in `chopsticks/scenarios/`

## Configuration

### S3 Configuration (`config/s3_config.yaml`)

- `endpoint`: S3 endpoint URL
- `access_key`: Access key ID
- `secret_key`: Secret access key
- `bucket`: Default bucket name
- `region`: AWS region (optional, default: us-east-1)
- `driver`: Driver to use (default: s5cmd)
- `driver_config`: Driver-specific configuration

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run black chopsticks/

# Lint code
uv run ruff check chopsticks/
```

## License

MIT
