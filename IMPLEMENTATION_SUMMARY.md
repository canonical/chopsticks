# S3 Scenario Test Implementation Summary

## Overview
This document summarizes the implementation of Phase 1 S3 stress test scenarios for the Chopsticks framework.

## Implemented Scenarios

### 1. Small Objects Scenario
**File**: `src/chopsticks/scenarios/s3/small_objects.py`  
**Config**: `config/scenarios/small_objects.yaml`

**Purpose**: Test high-frequency operations on small objects (1KB-100KB) to evaluate IOPS and metadata performance.

**Characteristics**:
- Object size range: 1KB - 100KB (randomized)
- Operation distribution: 70% upload, 20% download, 10% delete
- Recommended concurrency: 20 users, spawn rate 5/sec
- Target workloads: IoT data ingestion, log aggregation, microservices cache

**Key Metrics**:
- Operations per second (IOPS)
- Metadata operation latency
- Success rate under high-frequency operations

### 2. Mixed Workload Scenario
**File**: `src/chopsticks/scenarios/s3/mixed_workload.py`  
**Config**: `config/scenarios/mixed_workload.yaml`

**Purpose**: Simulate realistic production environments with varied object sizes and operation types.

**Characteristics**:
- Object size distribution:
  - 60% small (1KB-100KB)
  - 30% medium (100KB-10MB)
  - 10% large (10MB-100MB)
- Operation distribution: 50% upload, 35% download, 10% list, 5% delete
- Recommended concurrency: 15 users, spawn rate 3/sec
- Target workloads: General-purpose storage, web applications, content delivery

**Key Metrics**:
- Per-size-class performance
- Operation type latency distribution
- Throughput across varied object sizes

### 3. Concurrent Access Scenario
**File**: `src/chopsticks/scenarios/s3/concurrent_access.py`  
**Config**: `config/scenarios/concurrent_access.yaml`

**Purpose**: Test concurrency control and caching with multiple users accessing shared objects.

**Characteristics**:
- Pre-populated shared object pool: 100 objects (1MB each)
- Operation distribution: 80% read, 10% list, 10% write (read-heavy)
- Recommended concurrency: 50 users, spawn rate 10/sec
- Target workloads: Content delivery, CDN origins, shared datasets

**Key Metrics**:
- Read contention latency
- Cache performance (observable via response time variance)
- Concurrent operation success rate
- Object access frequency distribution

## Architecture

### Scenario Structure
All scenarios follow a consistent structure:
```python
# Configuration dictionary
TEST_CONFIG = {
    "scenario_name": "...",
    "parameters": {...}
}

# Global metrics collector
metrics_collector = None

# Locust event handlers
@events.init.add_listener
def on_test_start(environment, **kwargs):
    # Initialize metrics collection

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    # Export metrics and summary

# User class inheriting from S3Workload
class ScenarioUser(S3Workload):
    @task(weight)
    def operation(self):
        # Implement operation with metrics
```

### Integration with Metrics System
All scenarios integrate with the existing `MetricsCollector` system:
- Record operation results with `OperationResult` objects
- Track success/failure rates
- Measure latency and throughput
- Export metrics to JSON files
- Support Prometheus exposition (when enabled)

### Configuration Files
YAML configuration files in `config/scenarios/` provide:
- S3 endpoint configuration (endpoint, keys, region, bucket)
- Scenario-specific parameters
- Load configuration (users, spawn rate, duration)
- Metrics settings (Prometheus port, export interval)

## Usage Examples

### Small Objects Test
```bash
# Interactive mode
uv run locust -f src/chopsticks/scenarios/s3/small_objects.py

# Headless mode (10 minutes)
uv run locust -f src/chopsticks/scenarios/s3/small_objects.py \
    --headless -u 20 -r 5 -t 10m
```

### Mixed Workload Test
```bash
# Headless mode with custom parameters
uv run locust -f src/chopsticks/scenarios/s3/mixed_workload.py \
    --headless -u 15 -r 3 -t 10m
```

### Concurrent Access Test
```bash
# High concurrency test
uv run locust -f src/chopsticks/scenarios/s3/concurrent_access.py \
    --headless -u 50 -r 10 -t 10m
```

## Design Principles

1. **Extensibility**: Easy to add new scenarios by inheriting from `S3Workload`
2. **Consistency**: All scenarios follow the same structure and patterns
3. **Metrics Integration**: Comprehensive metrics collection built-in
4. **Configuration-Driven**: YAML configs separate from code
5. **Production-Realistic**: Scenarios mirror real-world usage patterns
6. **Flexible**: Support for interactive and headless modes

## Future Enhancements

See [SCENARIO_PROPOSALS.md](SCENARIO_PROPOSALS.md) for complete roadmap including:
- Phase 2: Multipart upload, large bucket operations, bandwidth saturation
- Phase 3: Metadata-only operations, directory simulation, versioning
- Phase 4: Lifecycle stress, failure injection
