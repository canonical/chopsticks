# S3 Workload Scenario Proposals

## Overview
This document proposes additional S3 stress test scenarios to complement the existing `s3_large_objects_with_metrics` scenario. Each scenario targets different usage patterns and performance characteristics of Ceph's S3 interface.

---

## Implemented Scenarios

### 1. Large Object Scenario ✅
**File:** `s3_large_objects_with_metrics.py`

**Description:** Uploads, downloads, and deletes large objects (10MB+) to test sequential I/O performance.

**Use Case:** Backup systems, video storage, archival workloads.

**Key Metrics:**
- Upload/download throughput for large files
- End-to-end latency for multi-MB objects
- Success rate under sustained load

---

## Proposed Scenarios

### 2. Small Object Scenario
**Proposed File:** `s3_small_objects_with_metrics.py`

**Description:** High-frequency operations on small objects (1KB-100KB) to simulate metadata-heavy workloads.

**Parameters:**
- Object size range: 1KB - 100KB (random or fixed)
- Operations: 70% upload, 20% download, 10% delete
- Higher concurrency than large objects

**Use Case:** IoT data ingestion, log aggregation, microservices cache.

**Key Metrics:**
- Operations per second (IOPS)
- Metadata operation latency
- Connection overhead ratio

**Implementation Notes:**
- Use smaller object sizes in `TestConfiguration`
- Increase user count for higher concurrency
- Track object count alongside data volume

---

### 3. Mixed Workload Scenario
**Proposed File:** `s3_mixed_workload_with_metrics.py`

**Description:** Realistic mix of object sizes and operation types to simulate production environments.

**Parameters:**
- Object size distribution:
  - 60% small (1KB-100KB)
  - 30% medium (100KB-10MB)
  - 10% large (10MB-100MB)
- Operation distribution:
  - 50% upload
  - 35% download
  - 10% list
  - 5% delete

**Use Case:** General-purpose object storage, web applications, content delivery.

**Key Metrics:**
- Per-size-class performance
- Operation type latency distribution
- Resource utilization patterns

**Implementation Notes:**
- Weighted random selection for object sizes
- Separate metric tracking per size class
- Dynamic task weights

---

### 4. Multipart Upload Scenario
**Proposed File:** `s3_multipart_upload_with_metrics.py`

**Description:** Tests S3 multipart upload API for very large objects (100MB+) split into chunks.

**Parameters:**
- Total object size: 100MB - 1GB
- Part size: 5MB - 50MB
- Concurrent part uploads: configurable
- Operations: initiate, upload parts, complete, abort

**Use Case:** Large file uploads, video processing, big data pipelines.

**Key Metrics:**
- Part upload parallelism efficiency
- Multipart completion success rate
- Time to first/last byte per part
- Abort/cleanup handling

**Implementation Notes:**
- Requires s5cmd multipart support or boto3 driver
- Track per-part and aggregate metrics
- Handle partial failures gracefully

---

### 5. Versioning Scenario
**Proposed File:** `s3_versioning_with_metrics.py`

**Description:** Tests versioned object operations to evaluate versioning overhead and performance.

**Parameters:**
- Versioning enabled on bucket
- Operations: PUT (creates versions), GET specific versions, list versions, delete versions
- Version depth: 5-20 versions per object

**Use Case:** Document management, audit trails, compliance systems.

**Key Metrics:**
- Version creation overhead
- Version retrieval latency
- List versions performance vs object count
- Storage overhead tracking (if accessible)

**Implementation Notes:**
- Requires versioning-enabled bucket
- Track version IDs in test state
- Measure LIST performance degradation

---

### 6. Lifecycle Stress Scenario
**Proposed File:** `s3_lifecycle_stress_with_metrics.py`

**Description:** Long-running test that continuously creates and deletes objects to test bucket lifecycle management.

**Parameters:**
- Object churn rate: X objects/minute
- Retention period: 1-24 hours (simulated with immediate delete)
- Operations: continuous upload → tag → delete cycle
- Object count: maintain N active objects

**Use Case:** Temporary storage, cache invalidation, log rotation.

**Key Metrics:**
- Sustained write throughput
- Delete operation efficiency
- Bucket stability under churn
- Object count consistency

**Implementation Notes:**
- Background deletion task
- Track object age/lifecycle
- Monitor for resource leaks

---

### 7. Concurrent Access Scenario
**Proposed File:** `s3_concurrent_access_with_metrics.py`

**Description:** Multiple users simultaneously accessing the same set of objects to test concurrency control and caching.

**Parameters:**
- Shared object set: 100-1000 objects
- User count: high (50+)
- Operations: 80% read (GET), 10% list, 10% write (PUT)
- Read-heavy workload

**Use Case:** Content delivery, shared datasets, collaborative platforms.

**Key Metrics:**
- Read contention latency
- Cache hit rate (observable via response time variance)
- List operation consistency under concurrent writes
- Lock/conflict rate

**Implementation Notes:**
- Pre-populate shared objects
- Coordinate user access patterns
- Track per-object access frequency

---

### 8. Large Bucket Scenario
**Proposed File:** `s3_large_bucket_with_metrics.py`

**Description:** Tests performance with a bucket containing millions of objects by simulating prefix-based navigation.

**Parameters:**
- Pre-population: seed bucket with 100K+ objects
- Operations: list with prefix/delimiter, paginated listing
- Prefix distribution: hierarchical (folders)
- Deep prefix depth: 5+ levels

**Use Case:** Data lakes, multi-tenant systems, hierarchical namespaces.

**Key Metrics:**
- List latency vs bucket object count
- Prefix filtering efficiency
- Pagination performance
- First page vs subsequent pages

**Implementation Notes:**
- Requires pre-seeding phase (script or initial task)
- Use consistent prefix scheme
- Track listing page sizes

---

### 9. Bandwidth Saturation Scenario
**Proposed File:** `s3_bandwidth_saturation_with_metrics.py`

**Description:** Attempts to saturate network bandwidth with sustained uploads/downloads to find throughput limits.

**Parameters:**
- Object size: optimized for throughput (10-100MB)
- Parallel transfers: ramping up until saturation
- Operations: simultaneous upload and download
- Duration: sustained (30+ minutes)

**Use Case:** Backup/restore, bulk data migration, replication.

**Key Metrics:**
- Peak aggregate throughput (MB/s)
- Saturation point (user count)
- Per-connection throughput
- Network efficiency (actual vs theoretical)

**Implementation Notes:**
- Ramp-up user count dynamically
- Monitor system resources
- Requires network monitoring integration

---

### 10. Metadata-Only Scenario
**Proposed File:** `s3_metadata_only_with_metrics.py`

**Description:** Focuses on metadata operations without data transfer to isolate control plane performance.

**Parameters:**
- Operations: HEAD object, list objects, get object metadata, set object tags
- No GET/PUT of object data
- High operation frequency
- Small or zero-byte objects

**Use Case:** Inventory systems, monitoring tools, metadata catalogs.

**Key Metrics:**
- Metadata operation latency
- Operations per second
- Control plane vs data plane separation
- API response overhead

**Implementation Notes:**
- Create objects once, then metadata ops only
- Use zero-byte or minimal objects
- Focus on API latency

---

### 11. Failure Injection Scenario
**Proposed File:** `s3_failure_injection_with_metrics.py`

**Description:** Intentionally triggers failures to test error handling and retry logic.

**Parameters:**
- Failure types: network timeout, invalid credentials, non-existent objects
- Failure rate: 5-20% of operations
- Operations: all types with random failures
- Retry configuration: track retry behavior

**Use Case:** Resilience testing, chaos engineering, SLA validation.

**Key Metrics:**
- Failure detection time
- Retry success rate
- Recovery time per failure type
- Error propagation patterns

**Implementation Notes:**
- Simulate failures at driver level
- Track retry attempts in metrics
- Categorize failure types

---

### 12. Directory Simulation Scenario
**Proposed File:** `s3_directory_simulation_with_metrics.py`

**Description:** Simulates filesystem-like operations using S3 prefixes as directories.

**Parameters:**
- Operations: create "directory" (PUT empty object with `/`), list directory, rename (copy + delete), recursive delete
- Hierarchy depth: 3-7 levels
- Files per directory: 10-1000
- Directory operations: create, list, move, delete

**Use Case:** S3-backed filesystems, S3FS, data migration tools.

**Key Metrics:**
- Directory listing performance
- Recursive operation efficiency
- Move operation latency (copy + delete)
- Hierarchy depth impact

**Implementation Notes:**
- Use prefix patterns (`path/to/dir/`)
- Implement rename as copy + delete
- Track hierarchy navigation

---

## Implementation Priority

### Phase 1 (High Impact)
1. **Small Object Scenario** - Complements large object test
2. **Mixed Workload Scenario** - Most realistic
3. **Concurrent Access Scenario** - Tests scalability

### Phase 2 (Advanced Features)
4. **Multipart Upload Scenario** - Requires driver enhancement
5. **Large Bucket Scenario** - Requires pre-seeding
6. **Bandwidth Saturation Scenario** - Performance limits

### Phase 3 (Specialized)
7. **Metadata-Only Scenario** - Control plane focus
8. **Directory Simulation Scenario** - Filesystem use case
9. **Versioning Scenario** - Feature-specific

### Phase 4 (Reliability)
10. **Lifecycle Stress Scenario** - Long-running stability
11. **Failure Injection Scenario** - Resilience testing

---

## Scenario Template Structure

Each scenario should follow this structure:

```python
"""
S3 [Scenario Name] Stress Test

Description: [Detailed description]

Use Case: [Target use case]

Configuration:
- object_size: [size or range]
- operation_distribution: [percentages]
- special_parameters: [scenario-specific]
"""

from locust import events
from chopsticks.metrics.collector import MetricsCollector
from chopsticks.metrics.models import TestConfiguration, OperationType
# ... imports

# Configuration
TEST_CONFIG = {
    "scenario_name": "[scenario_name]",
    # ... scenario-specific config
}

# Global metrics collector
metrics_collector = None

@events.init.add_listener
def on_test_start(environment, **kwargs):
    # Initialize metrics
    pass

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    # Export metrics and summary
    pass

class [ScenarioName]User(S3Workload):
    """
    Simulated user for [scenario description]
    """
    
    def __init__(self, environment):
        super().__init__(environment)
        # Scenario-specific initialization
        
    @task([weight])
    def [operation_name](self):
        """[Operation description]"""
        # Implementation with metrics
        
    def on_stop(self):
        """Cleanup"""
        pass
```

---

## Metrics Considerations

All scenarios should collect:

**Core Metrics:**
- Operation latency (P50, P95, P99)
- Success/failure rate
- Throughput (ops/sec, MB/s)
- Object size distribution

**Scenario-Specific Metrics:**
- Small objects: IOPS, metadata latency
- Multipart: part-level metrics
- Concurrent: contention indicators
- Large bucket: list pagination stats

**Prometheus Exposition:**
All metrics should be exposed via HTTP endpoint for real-time monitoring.

---

## Testing Recommendations

### Local Development
```bash
# Quick test (2 minutes, low load)
uv run chopsticks --config config/[scenario]_dev.yaml --duration 2m

# Full test (10 minutes, production-like)
uv run chopsticks --config config/[scenario]_prod.yaml --duration 10m
```

### CI/CD Integration
- Use 2-minute duration for PR checks
- Focus on success rate and basic metrics
- Full scenarios run nightly or on-demand

### Production Validation
- 30+ minute sustained tests
- Gradual ramp-up of users
- Monitor Ceph cluster health alongside
- Compare across scenarios to identify bottlenecks

---

## Future Considerations

### Multi-Protocol Testing
- RBD workload scenarios (block storage)
- CephFS scenarios (filesystem)
- Cross-protocol interactions

### Advanced Metrics
- Ceph cluster metrics integration (optional)
- Client-side resource usage (CPU, memory, network)
- Cost modeling (if applicable)

### Automation
- Scenario selection matrix
- Automated regression detection
- Performance baseline tracking
