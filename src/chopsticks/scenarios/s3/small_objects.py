"""
S3 Small Object Stress Test

Description: High-frequency operations on small objects (1KB-100KB) to simulate 
metadata-heavy workloads and test IOPS performance.

Use Case: IoT data ingestion, log aggregation, microservices cache, monitoring systems.

Configuration:
- object_size: 1KB - 100KB (randomized)
- operation_distribution: 70% upload, 20% download, 10% delete
- high_concurrency: designed for high user count
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
    "scenario_name": "s3_small_objects",
    "object_size_min_kb": 1,
    "object_size_max_kb": 100,
    "operations": {
        "upload": 70,
        "download": 20,
        "delete": 10,
    },
}

# Global metrics collector
metrics_collector = None
uploaded_objects = []


@events.init.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics collector when test starts."""
    global metrics_collector
    
    test_config = TestConfiguration(
        scenario_name=TEST_CONFIG["scenario_name"],
        workload_type="s3",
        client_driver="s5cmd",
        object_size_bytes=TEST_CONFIG["object_size_min_kb"] * 1024,
        duration_seconds=0,
        concurrency=environment.runner.target_user_count if environment.runner else 1,
    )
    
    metrics_collector = MetricsCollector(test_config)
    print(f"\n{'='*80}")
    print(f"Starting S3 Small Objects Stress Test")
    print(f"{'='*80}")
    print(f"Object Size Range: {TEST_CONFIG['object_size_min_kb']}KB - {TEST_CONFIG['object_size_max_kb']}KB")
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
        
        metrics_collector.export_to_file("small_objects_metrics.json")
        print("\nMetrics exported to: small_objects_metrics.json")


class SmallObjectUser(S3Workload):
    """
    Simulated user performing high-frequency small object operations.
    Focuses on IOPS and metadata performance.
    """
    
    def __init__(self, environment):
        super().__init__(environment)
        self.uploaded_files = []
        self.operation_count = 0
    
    def _get_random_size(self):
        """Generate random object size between min and max KB."""
        size_kb = random.randint(
            TEST_CONFIG["object_size_min_kb"],
            TEST_CONFIG["object_size_max_kb"]
        )
        return size_kb * 1024
    
    @task(70)
    def upload_small_object(self):
        """Upload a small object (1KB-100KB)."""
        object_size = self._get_random_size()
        object_name = f"small-{int(time.time() * 1000)}-{random.randint(1000, 9999)}.dat"
        
        start_time = time.time()
        try:
            result = self.upload_object(object_name, object_size)
            elapsed = time.time() - start_time
            
            if result["success"]:
                self.uploaded_files.append(object_name)
                uploaded_objects.append(object_name)
                
                if metrics_collector:
                    metrics_collector.record_operation(
                        OperationResult(
                            operation_type=OperationType.UPLOAD,
                            success=True,
                            duration_seconds=elapsed,
                            object_size_bytes=object_size,
                            timestamp=start_time,
                        )
                    )
            else:
                if metrics_collector:
                    metrics_collector.record_operation(
                        OperationResult(
                            operation_type=OperationType.UPLOAD,
                            success=False,
                            duration_seconds=elapsed,
                            object_size_bytes=object_size,
                            timestamp=start_time,
                            error_message=result.get("error", "Unknown error"),
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
    
    @task(20)
    def download_small_object(self):
        """Download a random small object."""
        available_objects = self.uploaded_files if self.uploaded_files else uploaded_objects
        
        if not available_objects:
            return
        
        object_name = random.choice(available_objects)
        
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
    def delete_small_object(self):
        """Delete a random small object."""
        if self.uploaded_files:
            object_name = self.uploaded_files.pop(random.randrange(len(self.uploaded_files)))
        elif uploaded_objects:
            object_name = uploaded_objects.pop(random.randrange(len(uploaded_objects)))
        else:
            return
        
        start_time = time.time()
        try:
            result = self.delete_object(object_name)
            elapsed = time.time() - start_time
            
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.DELETE,
                        success=result["success"],
                        duration_seconds=elapsed,
                        object_size_bytes=0,
                        timestamp=start_time,
                        error_message=result.get("error") if not result["success"] else None,
                    )
                )
        except Exception as e:
            elapsed = time.time() - start_time
            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.DELETE,
                        success=False,
                        duration_seconds=elapsed,
                        object_size_bytes=0,
                        timestamp=start_time,
                        error_message=str(e),
                    )
                )
    
    def on_stop(self):
        """Cleanup uploaded files when user stops."""
        for object_name in self.uploaded_files:
            try:
                self.delete_object(object_name)
            except Exception:
                pass
