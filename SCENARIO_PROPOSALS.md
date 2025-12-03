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

## 6. Multipart Upload Scenario
**Purpose**: Test large file uploads using multipart upload functionality.

**Test Pattern**:
- Upload files using multipart upload (5MB parts)
- Test different part sizes and file sizes
- Verify upload completion and integrity

**Key Metrics**:
- Multipart upload success rate
- Part upload latency
- Complete multipart operation time
- Bandwidth utilization

**Configuration**:
```yaml
scenario: multipart_upload
file_sizes:
  - 100MB
  - 500MB
  - 1GB
part_size: 5MB
concurrent_uploads: 10
```

## 7. Versioning Operations Scenario
**Purpose**: Test S3 versioning capabilities and object version management.

**Test Pattern**:
- Enable versioning on buckets
- Create multiple versions of same objects
- List and retrieve specific versions
- Delete specific versions

**Key Metrics**:
- Version creation rate
- Version retrieval latency
- List versions operation time
- Storage overhead

**Configuration**:
```yaml
scenario: versioning_ops
objects_per_key: 10  # versions
operations:
  - put: 60%
  - get_version: 20%
  - list_versions: 15%
  - delete_version: 5%
```

## 8. Lifecycle and Expiration Scenario
**Purpose**: Test object lifecycle policies and expiration rules.

**Test Pattern**:
- Set lifecycle policies on buckets
- Create objects with expiration tags
- Verify policy application
- Monitor object transitions

**Key Metrics**:
- Policy application success rate
- Transition operation latency
- Expiration accuracy

**Configuration**:
```yaml
scenario: lifecycle_ops
policies:
  - transition_after_days: 7
  - expire_after_days: 30
object_count: 10000
```

## 9. Metadata Operations Scenario
**Purpose**: Stress test object metadata operations (tags, ACLs, metadata headers).

**Test Pattern**:
- Set/get object tags
- Modify object ACLs
- Update custom metadata
- Query objects by metadata

**Key Metrics**:
- Metadata operation latency
- Tag query performance
- ACL modification success rate

**Configuration**:
```yaml
scenario: metadata_ops
operations:
  - put_tags: 30%
  - get_tags: 30%
  - put_acl: 20%
  - get_acl: 20%
tags_per_object: 10
```

## 10. Bucket Operations Scenario
**Purpose**: Test bucket-level operations at scale.

**Test Pattern**:
- Create/delete buckets
- List bucket contents
- Set bucket policies
- Configure bucket properties

**Key Metrics**:
- Bucket creation/deletion rate
- List operation latency with varying object counts
- Policy application time

**Configuration**:
```yaml
scenario: bucket_ops
bucket_count: 100
objects_per_bucket: 1000
operations:
  - create_bucket: 10%
  - delete_bucket: 10%
  - list_objects: 50%
  - put_policy: 20%
  - get_policy: 10%
```

## 11. Stress and Spike Scenario
**Purpose**: Test cluster behavior under sudden load spikes and sustained stress.

**Test Pattern**:
- Gradual ramp-up to baseline load
- Sudden spike to 10x load
- Sustained high load period
- Gradual ramp-down

**Key Metrics**:
- Error rate during spikes
- Recovery time after spike
- Throughput degradation
- Latency percentiles (p95, p99)

**Configuration**:
```yaml
scenario: stress_spike
baseline_users: 10
spike_users: 100
spike_duration: 2min
sustained_duration: 5min
ramp_time: 1min
```

## 12. Data Integrity Verification Scenario
**Purpose**: Verify data integrity across operations.

**Test Pattern**:
- Upload objects with checksums
- Download and verify checksums
- Perform corruption detection
- Test ETag validation

**Key Metrics**:
- Checksum verification success rate
- Data corruption incidents
- ETag mismatch count

**Configuration**:
```yaml
scenario: data_integrity
checksum_algorithm: sha256
verification_sample_rate: 100%
object_sizes: [1KB, 1MB, 10MB, 100MB]
```

## 13. Cross-Region Replication Scenario (if applicable)
**Purpose**: Test replication performance and consistency.

**Test Pattern**:
- Configure bucket replication
- Upload objects to source bucket
- Verify replication to target
- Measure replication lag

**Key Metrics**:
- Replication lag time
- Replication success rate
- Bandwidth consumption

**Configuration**:
```yaml
scenario: replication
source_region: us-east-1
target_region: us-west-2
object_count: 10000
verify_consistency: true
```

## 14. Error and Retry Scenario
**Purpose**: Test error handling and retry mechanisms.

**Test Pattern**:
- Simulate network failures
- Test with invalid credentials
- Exceed rate limits
- Handle partial failures

**Key Metrics**:
- Retry success rate
- Error recovery time
- Graceful degradation

**Configuration**:
```yaml
scenario: error_handling
error_injection_rate: 5%
retry_policy:
  max_attempts: 3
  backoff: exponential
```

## Implementation Priority

Recommended implementation order based on common use cases:

1. **Phase 1** (Essential):
   - Large Object Test ✅ (Already implemented)
   - Mixed Workload
   - Concurrent Read/Write

2. **Phase 2** (Common Use Cases):
   - Small Object Test
   - Metadata Operations
   - Bucket Operations

3. **Phase 3** (Advanced):
   - Multipart Upload
   - Versioning Operations
   - Stress and Spike

4. **Phase 4** (Specialized):
   - Data Integrity Verification
   - Lifecycle Operations
   - Error and Retry
   - Cross-Region Replication (if applicable)

## Extensibility Guidelines

When adding new scenarios:

1. Create a new scenario file in `src/chopsticks/scenarios/s3/`
2. Inherit from `BaseS3Scenario`
3. Implement required task methods
4. Add scenario configuration to `config/scenarios/`
5. Update documentation
6. Add unit tests
7. Add functional tests if needed

Example structure:
```python
from chopsticks.scenarios.s3.base import BaseS3Scenario

class MyCustomScenario(BaseS3Scenario):
    """Description of scenario."""
    
    @task(weight=70)
    def primary_operation(self):
        """Main operation."""
        pass
    
    @task(weight=30)
    def secondary_operation(self):
        """Secondary operation."""
        pass
```
