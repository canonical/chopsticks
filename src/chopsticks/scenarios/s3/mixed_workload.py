"""
S3 Mixed Workload Stress Test

Description: Realistic mix of object sizes and operation types to simulate
production environments with varied traffic patterns.

Use Case: General-purpose object storage, web applications, content delivery,
multi-tenant systems.

Configuration:
- object_size_distribution: 60% small (1KB-100KB), 30% medium (100KB-10MB), 10% large (10MB-100MB)
- operation_distribution: 50% upload, 35% download, 10% list, 5% delete
"""

import random
import time
from locust import task, events
from chopsticks.workloads.s3.workload import S3Workload
from chopsticks.metrics.collector import MetricsCollector
from chopsticks.metrics.models import (
    TestConfiguration,
    OperationType,
    OperationMetric,
)

# Configuration
TEST_CONFIG = {
    "scenario_name": "s3_mixed_workload",
    "object_size_distribution": {
        "small": {"weight": 60, "min_kb": 1, "max_kb": 100},
        "medium": {"weight": 30, "min_kb": 100, "max_kb": 10240},
        "large": {"weight": 10, "min_kb": 10240, "max_kb": 102400},
    },
    "operations": {
        "upload": 50,
        "download": 35,
        "list": 10,
        "delete": 5,
    },
}

# Global state
metrics_collector = None
uploaded_objects: dict[str, list[str]] = {"small": [], "medium": [], "large": []}


@events.init.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics collector when test starts."""
    global metrics_collector

    test_config = TestConfiguration(
        scenario_name=TEST_CONFIG["scenario_name"],
        workload_type="s3",
        client_driver="s5cmd",
        object_size_bytes=0,
        duration_seconds=0,
        concurrency=environment.runner.target_user_count if environment.runner else 1,
    )

    metrics_collector = MetricsCollector(test_config)
    print(f"\n{'=' * 80}")
    print("Starting S3 Mixed Workload Stress Test")
    print(f"{'=' * 80}")
    print("Object Size Distribution:")
    for size_class, config in TEST_CONFIG["object_size_distribution"].items():
        print(
            f"  {size_class}: {config['weight']}% ({config['min_kb']}KB - {config['max_kb']}KB)"
        )
    print(f"Operation Distribution: {TEST_CONFIG['operations']}")
    print(f"{'=' * 80}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export metrics and summary when test stops."""
    global metrics_collector

    if metrics_collector:
        print(f"\n{'=' * 80}")
        print("Test Completed - Exporting Metrics")
        print(f"{'=' * 80}\n")

        summary = metrics_collector.get_summary()
        print(summary)

        metrics_collector.export_to_file("mixed_workload_metrics.json")
        print("\nMetrics exported to: mixed_workload_metrics.json")


class MixedWorkloadUser(S3Workload):
    """
    Simulated user performing mixed workload operations.
    Handles varied object sizes and operation types.
    """

    def __init__(self, environment):
        super().__init__(environment)
        self.uploaded_files = {"small": [], "medium": [], "large": []}

    def _get_random_object_size(self):
        """Select object size based on distribution weights."""
        rand = random.randint(1, 100)
        cumulative = 0

        for size_class, config in TEST_CONFIG["object_size_distribution"].items():
            cumulative += config["weight"]
            if rand <= cumulative:
                size_kb = random.randint(config["min_kb"], config["max_kb"])
                return size_kb * 1024, size_class

        return 1024, "small"

    @task(50)
    def upload_object_mixed(self):
        """Upload an object with size chosen from distribution."""
        object_size, size_class = self._get_random_object_size()
        object_name = f"mixed-{size_class}-{int(time.time() * 1000)}-{random.randint(1000, 9999)}.dat"

        start_time = time.time()
        try:
            result = self.upload_object(object_name, object_size)
            elapsed = time.time() - start_time

            if result["success"]:
                self.uploaded_files[size_class].append(object_name)
                uploaded_objects[size_class].append(object_name)

                if metrics_collector:
                    metrics_collector.record_operation(
                        OperationResult(
                            operation_type=OperationType.UPLOAD,
                            success=True,
                            duration_seconds=elapsed,
                            object_size_bytes=object_size,
                            timestamp=start_time,
                            metadata={"size_class": size_class},
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
                            metadata={"size_class": size_class},
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

    @task(35)
    def download_object_mixed(self):
        """Download a random object from any size class."""
        all_objects = []
        for size_class in ["small", "medium", "large"]:
            all_objects.extend(self.uploaded_files[size_class])
            all_objects.extend(uploaded_objects[size_class])

        if not all_objects:
            return

        object_name = random.choice(all_objects)

        start_time = time.time()
        try:
            result = self.download_object(object_name)
            elapsed = time.time() - start_time

            object_size = result.get("size", 0)

            size_class = "unknown"
            if "small" in object_name:
                size_class = "small"
            elif "medium" in object_name:
                size_class = "medium"
            elif "large" in object_name:
                size_class = "large"

            if metrics_collector:
                metrics_collector.record_operation(
                    OperationResult(
                        operation_type=OperationType.DOWNLOAD,
                        success=result["success"],
                        duration_seconds=elapsed,
                        object_size_bytes=object_size,
                        timestamp=start_time,
                        error_message=result.get("error")
                        if not result["success"]
                        else None,
                        metadata={"size_class": size_class},
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
    def list_objects_mixed(self):
        """List objects in the bucket."""
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
                        error_message=result.get("error")
                        if not result["success"]
                        else None,
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

    @task(5)
    def delete_object_mixed(self):
        """Delete a random object from any size class."""
        available_size_classes = [
            sc
            for sc in ["small", "medium", "large"]
            if self.uploaded_files[sc] or uploaded_objects[sc]
        ]

        if not available_size_classes:
            return

        size_class = random.choice(available_size_classes)

        if self.uploaded_files[size_class]:
            object_name = self.uploaded_files[size_class].pop(
                random.randrange(len(self.uploaded_files[size_class]))
            )
        else:
            object_name = uploaded_objects[size_class].pop(
                random.randrange(len(uploaded_objects[size_class]))
            )

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
                        error_message=result.get("error")
                        if not result["success"]
                        else None,
                        metadata={"size_class": size_class},
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
        for size_class in ["small", "medium", "large"]:
            for object_name in self.uploaded_files[size_class]:
                try:
                    self.delete_object(object_name)
                except Exception:
                    pass
