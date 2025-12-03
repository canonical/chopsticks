"""
S3 Mixed Workload Stress Test with Metrics

Description: Realistic mix of object sizes and operation types to simulate
production S3 environments with diverse access patterns.

Use Case: General-purpose object storage, web applications, content delivery

Configuration:
- object_size_distribution:
  * 60% small (1KB-100KB)
  * 30% medium (100KB-10MB)
  * 10% large (10MB-100MB)
- operation_distribution:
  * 50% upload
  * 35% download
  * 10% list
  * 5% delete
"""

import os
import random
from datetime import datetime
from locust import events, task

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics.collector import MetricsCollector
from chopsticks.metrics.http_server import start_metrics_server
from chopsticks.metrics.models import (
    TestConfiguration,
    OperationType,
    WorkloadType,
)

# Configuration - Object size ranges in KB
SMALL_MIN = 1
SMALL_MAX = 100
MEDIUM_MIN = 100
MEDIUM_MAX = 10240  # 10MB
LARGE_MIN = 10240
LARGE_MAX = 102400  # 100MB

# Size distribution weights
SIZE_WEIGHTS = {
    "small": 60,
    "medium": 30,
    "large": 10,
}

METRICS_PORT = int(os.getenv("METRICS_PORT", "8090"))

# Global metrics collector
metrics_collector = None


@events.init.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics collection when test starts"""
    global metrics_collector

    test_config = TestConfiguration(
        workload_type=WorkloadType.S3,
        scenario_name="mixed_workload",
        target_endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        client_driver="s5cmd",
        test_parameters={
            "size_distribution": "60% small (1KB-100KB), 30% medium (100KB-10MB), 10% large (10MB-100MB)",
            "operation_distribution": "50% upload, 35% download, 10% list, 5% delete",
        },
    )

    metrics_collector = MetricsCollector(test_config)
    start_metrics_server(metrics_collector, METRICS_PORT)

    print(f"\n{'=' * 70}")
    print("Metrics Collection Initialized - Mixed Workload")
    print(f"{'=' * 70}")
    print(f"Test Run ID: {test_config.test_run_id}")
    print("Chopsticks Metrics Endpoint: http://0.0.0.0:8090/metrics")
    print(f"{'=' * 70}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Export metrics when test completes"""
    global metrics_collector

    if metrics_collector:
        try:
            csv_path = metrics_collector.export_to_csv()
            json_path = metrics_collector.export_to_json()

            summary = metrics_collector.get_summary()
            print(f"\n{'=' * 70}")
            print("Mixed Workload Test Summary")
            print(f"{'=' * 70}")
            print(f"Total Operations: {summary['operations']['total']}")
            print(f"Success Rate: {summary['operations']['success_rate']:.2f}%")
            print(f"Total Data: {summary['data']['total_mb']:.2f} MB")
            print(f"Avg Throughput: {summary['data']['throughput_mbps']:.2f} MB/s")
            print("\nOperation Breakdown:")
            for op_type, stats in summary["operations"]["by_type"].items():
                print(
                    f"  {op_type}: {stats['count']} ops, {stats['success_rate']:.1f}% success"
                )
            print("\nMetrics exported:")
            print(f"  CSV: {csv_path}")
            print(f"  JSON: {json_path}")
            print(f"{'=' * 70}\n")

        except Exception as e:
            print(f"Error exporting metrics: {e}")


class MixedWorkloadUser(S3Workload):
    """
    Simulated user with mixed object sizes and operations
    Represents realistic production workload patterns
    """

    def __init__(self, environment):
        super().__init__(environment)
        self.uploaded_objects = {
            "small": [],
            "medium": [],
            "large": [],
        }
        self.test_prefix = f"mixed-test/{environment.runner.user_count}/"

    def _select_size_class(self):
        """Randomly select size class based on distribution weights"""
        total = sum(SIZE_WEIGHTS.values())
        rand = random.randint(1, total)

        cumulative = 0
        for size_class, weight in SIZE_WEIGHTS.items():
            cumulative += weight
            if rand <= cumulative:
                return size_class
        return "small"

    def _generate_object_size(self, size_class):
        """Generate object size in KB based on size class"""
        if size_class == "small":
            return random.randint(SMALL_MIN, SMALL_MAX)
        elif size_class == "medium":
            return random.randint(MEDIUM_MIN, MEDIUM_MAX)
        else:  # large
            return random.randint(LARGE_MIN, LARGE_MAX)

    def _generate_object_data(self, size_kb):
        """Generate random data of specified size in KB"""
        return os.urandom(size_kb * 1024)

    def _record_metric(
        self, operation, object_key, size_bytes, start_time, end_time, success
    ):
        """Record operation metric"""
        global metrics_collector
        if metrics_collector:
            metrics_collector.record_operation(
                operation_type=operation,
                object_key=object_key,
                size_bytes=size_bytes,
                start_time=start_time,
                end_time=end_time,
                success=success,
            )

    @task(50)  # 50% upload operations
    def upload_mixed_object(self):
        """Upload object with size selected from distribution"""
        size_class = self._select_size_class()
        size_kb = self._generate_object_size(size_class)
        key = f"{self.test_prefix}{size_class}/{size_class}-{random.randint(1000, 999999)}.bin"
        data = self._generate_object_data(size_kb)

        start_time = datetime.utcnow()
        try:
            self.client.upload(key, data)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.UPLOAD,
                key,
                len(data),
                start_time,
                end_time,
                True,
            )
            self.uploaded_objects[size_class].append(key)
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.UPLOAD, key, len(data), start_time, end_time, False
            )
            raise e

    @task(35)  # 35% download operations
    def download_mixed_object(self):
        """Download a previously uploaded object"""
        # Get all uploaded keys
        all_keys = []
        for keys in self.uploaded_objects.values():
            all_keys.extend(keys)

        if not all_keys:
            return

        key = random.choice(all_keys)
        start_time = datetime.utcnow()

        try:
            data = self.client.download(key)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DOWNLOAD,
                key,
                len(data),
                start_time,
                end_time,
                True,
            )
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DOWNLOAD, key, 0, start_time, end_time, False
            )
            raise e

    @task(10)  # 10% list operations
    def list_objects(self):
        """List objects with prefix"""
        size_class = random.choice(["small", "medium", "large"])
        prefix = f"{self.test_prefix}{size_class}/"

        start_time = datetime.utcnow()
        try:
            self.client.list_objects(prefix=prefix, max_keys=100)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.LIST,
                prefix,
                0,
                start_time,
                end_time,
                True,
            )
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.LIST, prefix, 0, start_time, end_time, False
            )
            raise e

    @task(5)  # 5% delete operations
    def delete_mixed_object(self):
        """Delete a random object"""
        # Get all uploaded keys
        all_keys = []
        for size_class, keys in self.uploaded_objects.items():
            all_keys.extend([(size_class, key) for key in keys])

        if not all_keys:
            return

        size_class, key = random.choice(all_keys)
        start_time = datetime.utcnow()

        try:
            self.client.delete(key)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE, key, 0, start_time, end_time, True
            )
            self.uploaded_objects[size_class].remove(key)
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE, key, 0, start_time, end_time, False
            )
            raise e

    def on_stop(self):
        """Cleanup uploaded objects when user stops"""
        for keys in self.uploaded_objects.values():
            for key in keys[:]:
                try:
                    self.client.delete(key)
                except Exception:
                    pass
