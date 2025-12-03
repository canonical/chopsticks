# Chopsticks Quick Start Guide

## Installation

1. **Clone and setup:**
   ```bash
   cd chopsticks
   uv sync
   ```

2. **Install s5cmd (S3 client driver):**
   ```bash
   ./scripts/install_s5cmd.sh
   ```

## Configuration

1. **Copy the example config:**
   ```bash
   cp config/s3_config.yaml.example config/s3_config.yaml
   ```

2. **Edit configuration with your S3 credentials:**
   ```bash
   nano config/s3_config.yaml
   ```
   
   Update these fields:
   - `endpoint`: Your S3 endpoint (e.g., https://s3.amazonaws.com)
   - `access_key`: Your S3 access key
   - `secret_key`: Your S3 secret key
   - `bucket`: Test bucket name

## Running Tests

### 1. Web UI Mode (Interactive)

```bash
uv run locust -f src/chopsticks/scenarios/s3_large_objects.py
```

Then open http://localhost:8089 in your browser to:
- Set number of users
- Set spawn rate
- Start/stop tests
- View real-time metrics

### 2. Headless Mode (Automated)

```bash
# 10 concurrent users, spawn 2 per second, run for 5 minutes
uv run locust -f src/chopsticks/scenarios/s3_large_objects.py \
  --headless -u 10 -r 2 -t 5m
```

### 3. Distributed Mode

**On master node:**
```bash
uv run locust -f src/chopsticks/scenarios/s3_large_objects.py --master
```

**On worker nodes:**
```bash
uv run locust -f src/chopsticks/scenarios/s3_large_objects.py \
  --worker --master-host=<master-ip>
```

## Customizing Tests

### Adjust Object Size

```bash
# Test with 500MB objects instead of default 100MB
LARGE_OBJECT_SIZE=500 uv run locust -f src/chopsticks/scenarios/s3_large_objects.py
```

### Create Custom Scenario

See `src/chopsticks/scenarios/example_scenario.py` for a template.

```python
from locust import task, between
from chopsticks.workloads.s3.s3_workload import S3Workload

class MyTest(S3Workload):
    wait_time = between(1, 3)
    
    @task
    def my_test(self):
        key = self.generate_key()
        data = self.generate_data(1024 * 1024)  # 1MB
        self.client.upload(key, data)
```

Run it:
```bash
uv run locust -f my_scenario.py
```

## Metrics

Locust tracks:
- **Requests**: Total number of operations
- **Failures**: Failed operations
- **Response Time**: Min/Max/Median/95th percentile
- **RPS**: Requests per second
- **Users**: Current simulated users

## Troubleshooting

### s5cmd not found
```bash
export PATH=$HOME/.local/bin:$PATH
# Or specify in config:
# driver_config:
#   s5cmd_path: /full/path/to/s5cmd
```

### Connection errors
- Verify endpoint URL is correct
- Check credentials
- Ensure bucket exists
- Test network connectivity: `curl -v <endpoint>`

### Config not found
Set explicitly:
```bash
S3_CONFIG_PATH=/path/to/s3_config.yaml uv run locust -f scenario.py
```

## Next Steps

1. Read [DESIGN.md](DESIGN.md) for architecture details
2. Check [README.md](README.md) for advanced usage
3. Create custom scenarios for your workload
4. Add new drivers (boto3, minio, etc.)
5. Extend to RBD workloads
