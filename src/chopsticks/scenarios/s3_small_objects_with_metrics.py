"""
S3 Small Object Stress Test with Metrics

Description: High-frequency operations on small objects (1KB-100KB) to test
metadata-heavy workloads and IOPS performance.

Use Case: IoT data ingestion, log aggregation, microservices cache

Configuration:
- object_size: 1KB - 100KB
- operation_distribution: 70% upload, 20% download, 10% delete
- high_concurrency: optimized for metadata operations
"""

import os
import random
from datetime import datetime
from locust import events, task

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics.collector import MetricsCollector
from chopsticks.metrics.http_server import MetricsHTTPServer
from chopsticks.metrics.models import (
    TestConfiguration,
    OperationType,
    WorkloadType,
)

# Configuration
OBJECT_SIZE_MIN = int(os.getenv("SMALL_OBJECT_SIZE_MIN", "1"))  # KB
OBJECT_SIZE_MAX = int(os.getenv("SMALL_OBJECT_SIZE_MAX", "100"))  # KB
METRICS_PORT = int(os.getenv("METRICS_PORT", "8090"))

# Global metrics collector
metrics_collector = None


@events.init.add_listener
def on_test_start(environment, **kwargs):
    """Initialize metrics collection when test starts"""
    global metrics_collector

    test_config = TestConfiguration(
        workload_type=WorkloadType.S3,
        scenario_name="small_objects",
        target_endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        client_driver="s5cmd",
        test_parameters={
            "object_size_min_kb": OBJECT_SIZE_MIN,
            "object_size_max_kb": OBJECT_SIZE_MAX,
            "operation_distribution": "70% upload, 20% download, 10% delete",
        },
    )

    metrics_collector = MetricsCollector(test_config)

    # Start HTTP metrics server
    start_metrics_server(metrics_collector, METRICS_PORT)

    print(f"\n{'=' * 70}")
    print("Metrics Collection Initialized")
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
            # Export to files
            csv_path = metrics_collector.export_to_csv()
            json_path = metrics_collector.export_to_json()

            # Print summary
            summary = metrics_collector.get_summary()
            print(f"\n{'=' * 70}")
            print("Metrics Collection Summary")
            print(f"{'=' * 70}")
            print(f"Total Operations: {summary['operations']['total']}")
            print(f"Success Rate: {summary['operations']['success_rate']:.2f}%")
            print(f"Total Data Transferred: {summary['data']['total_mb']:.2f} MB")
            print(f"Average Throughput: {summary['data']['throughput_mbps']:.2f} MB/s")
            print("\nMetrics exported:")
            print(f"  CSV: {csv_path}")
            print(f"  JSON: {json_path}")
            print(f"{'=' * 70}\n")

        except Exception as e:
            print(f"Error exporting metrics: {e}")


class SmallObjectUser(S3Workload):
    """
    Simulated user performing small object operations
    Focus on high-frequency metadata-heavy workloads
    """

    def __init__(self, environment):
        super().__init__(environment)
        self.uploaded_keys = []
        self.test_prefix = f"small-objects-test/{environment.runner.user_count}/"

    def _generate_random_size(self):
        """Generate random object size between min and max"""
        return random.randint(OBJECT_SIZE_MIN, OBJECT_SIZE_MAX)

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

    @task(70)  # 70% weight - primary operation
    def upload_small_object(self):
        """Upload small object with random size"""
        size_kb = self._generate_random_size()
        key = f"{self.test_prefix}small-{size_kb}kb-{random.randint(1000, 999999)}.bin"
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
            self.uploaded_keys.append(key)
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.UPLOAD, key, len(data), start_time, end_time, False
            )
            raise e

    @task(20)  # 20% weight
    def download_small_object(self):
        """Download a previously uploaded small object"""
        if not self.uploaded_keys:
            return

        key = random.choice(self.uploaded_keys)
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

    @task(10)  # 10% weight
    def delete_small_object(self):
        """Delete a small object"""
        if not self.uploaded_keys:
            return

        key = self.uploaded_keys.pop(random.randrange(len(self.uploaded_keys)))
        start_time = datetime.utcnow()

        try:
            self.client.delete(key)
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE, key, 0, start_time, end_time, True
            )
        except Exception as e:
            end_time = datetime.utcnow()
            self._record_metric(
                OperationType.DELETE, key, 0, start_time, end_time, False
            )
            raise e

    def on_stop(self):
        """Cleanup uploaded objects when user stops"""
        for key in self.uploaded_keys[:]:
            try:
                self.client.delete(key)
            except Exception:
                pass
