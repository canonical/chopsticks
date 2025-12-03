"""
S3 Concurrent Access Stress Test

Description: Multiple users simultaneously accessing the same set of objects 
to test concurrency control, caching, and read-heavy workloads.

Use Case: Content delivery, shared datasets, collaborative platforms, 
CDN origin servers.

Configuration:
- shared_object_set: 100-1000 pre-populated objects
- high_concurrency: designed for 50+ users
- operation_distribution: 80% read (GET), 10% list, 10% write (PUT)
- read_heavy: optimized for concurrent reads
"""

import random
import time
from locust import task, events
from chopsticks.workloads.s3 import S3Workload
from chopsticks.metrics.collector import MetricsCollector
from chopsticks.metrics.models import (
    TestConfiguration,
    OperationType,
    OperationResult,
)

# Configuration
TEST_CONFIG = {
    "scenario_name": "s3_concurrent_access",
    "shared_object_count": 100,
    "object_size_kb": 1024,
    "operations": {
        "read": 80,
        "list": 10,
        "write": 10,
    },
}

# Global state
metrics_collector = None
shared_objects = []
initialization_done = False


@events.init.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics collector when test starts."""
    global metrics_collector
    
    test_config = TestConfiguration(
        scenario_name=TEST_CONFIG["scenario_name"],
        workload_type="s3",
        client_driver="s5cmd",
        object_size_bytes=TEST_CONFIG["object_size_kb"] * 1024,
        duration_seconds=0,
        concurrency=environment.runner.target_user_count if environment.runner else 1,
    )
    
    metrics_collector = MetricsCollector(test_config)
    print(f"\n{'='*80}")
    print(f"Starting S3 Concurrent Access Stress Test")
    print(f"{'='*80}")
    print(f"Shared Object Count: {TEST_CONFIG['shared_object_count']}")
    print(f"Object Size: {TEST_CONFIG['object_size_kb']}KB")
    print(f"Operation Distribution: {TEST_CONFIG['operations']}")
    print(f"{'='*80}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export metrics and summary when test stops."""
    global metrics_collector
    
    if metrics_collector:
        print(f"\n{'='*80}")
        print(f"Test Completed - Exporting Metrics")
        print(f"{'='*80}\n")
        
        summary = metrics_collector.get_summary()
        print(summary)
        
        metrics_collector.export_to_file("concurrent_access_metrics.json")
        print("\nMetrics exported to: concurrent_access_metrics.json")


class ConcurrentAccessUser(S3Workload):
    """
    Simulated user performing concurrent access to shared objects.
    Focuses on read performance and concurrency handling.
    """
    
    def __init__(self, environment):
        super().__init__(environment)
        self.access_counts = {}
        self._initialize_shared_objects()
    
    def _initialize_shared_objects(self):
        """Initialize shared objects pool (first user creates them)."""
        global shared_objects, initialization_done
        
        if initialization_done or len(shared_objects) >= TEST_CONFIG["shared_object_count"]:
            return
        
        initialization_done = True
        print(f"Initializing {TEST_CONFIG['shared_object_count']} shared objects...")
        
        for i in range(TEST_CONFIG["shared_object_count"]):
            object_name = f"shared-{i:04d}.dat"
            object_size = TEST_CONFIG["object_size_kb"] * 1024
            
            try:
                result = self.upload_object(object_name, object_size)
                if result["success"]:
                    shared_objects.append(object_name)
            except Exception as e:
                print(f"Failed to initialize object {object_name}: {e}")
        
        print(f"Initialized {len(shared_objects)} shared objects")
    
    @task(80)
    def read_shared_object(self):
        """Read a random shared object (high frequency)."""
        if not shared_objects:
            return
        
        object_name = random.choice(shared_objects)
        
        if object_name not in self.access_counts:
            self.access_counts[object_name] = 0
        self.access_counts[object_name] += 1
        
        start_time = time.time()
        try:
            result = self.download_object(object_name)
            elapsed = time.time() - start_time
            
            object_size = result.get("size", 0)
            
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.DOWNLOAD,
                        success=result["success"],
                        duration_seconds=elapsed,
                        object_size_bytes=object_size,
                        timestamp=start_time,
                        error_message=result.get("error") if not result["success"] else None,
                        metadata={
                            "object_name": object_name,
                            "access_count": self.access_counts[object_name],
                        },
                    )
                )
        except Exception as e:
            elapsed = time.time() - start_time
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.DOWNLOAD,
                        success=False,
                        duration_seconds=elapsed,
                        object_size_bytes=0,
                        timestamp=start_time,
                        error_message=str(e),
                    )
                )
    
    @task(10)
    def list_shared_objects(self):
        """List objects in the shared bucket."""
        start_time = time.time()
        try:
            result = self.list_objects()
            elapsed = time.time() - start_time
            
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.LIST,
                        success=result["success"],
                        duration_seconds=elapsed,
                        object_size_bytes=0,
                        timestamp=start_time,
                        error_message=result.get("error") if not result["success"] else None,
                        metadata={"object_count": result.get("count", 0)},
                    )
                )
        except Exception as e:
            elapsed = time.time() - start_time
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.LIST,
                        success=False,
                        duration_seconds=elapsed,
                        object_size_bytes=0,
                        timestamp=start_time,
                        error_message=str(e),
                    )
                )
    
    @task(10)
    def write_shared_object(self):
        """Overwrite a random shared object (low frequency)."""
        if not shared_objects:
            return
        
        object_name = random.choice(shared_objects)
        object_size = TEST_CONFIG["object_size_kb"] * 1024
        
        start_time = time.time()
        try:
            result = self.upload_object(object_name, object_size)
            elapsed = time.time() - start_time
            
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.UPLOAD,
                        success=result["success"],
                        duration_seconds=elapsed,
                        object_size_bytes=object_size,
                        timestamp=start_time,
                        error_message=result.get("error") if not result["success"] else None,
                        metadata={"object_name": object_name, "overwrite": True},
                    )
                )
        except Exception as e:
            elapsed = time.time() - start_time
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.UPLOAD,
                        success=False,
                        duration_seconds=elapsed,
                        object_size_bytes=object_size,
                        timestamp=start_time,
                        error_message=str(e),
                    )
                )
