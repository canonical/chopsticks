"""S3 Large Object Stress Test with Metrics"""

import os
import random
from datetime import datetime
from locust import task, between, events
import uuid

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics import (
    MetricsCollector,
    TestConfiguration,
    OperationType,
    WorkloadType,
)
from chopsticks.metrics.http_server import MetricsHTTPServer


metrics_server = None
metrics_collector = None
test_config = None


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collection when Locust starts"""
    global metrics_server, metrics_collector, test_config

    test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name="S3 Large Objects",
        start_time=datetime.utcnow(),
        scenario="large_objects",
        workload_type=WorkloadType.S3,
        test_config={
            "object_size_mb": int(os.getenv("LARGE_OBJECT_SIZE", "100")),
            "users": environment.parsed_options.num_users
            if hasattr(environment, "parsed_options")
            else 1,
        },
    )

    metrics_collector = MetricsCollector(
        test_run_id=test_config.test_run_id,
        test_config=test_config,
        aggregation_window_seconds=10,
    )

    port = int(os.getenv("METRICS_PORT", "9646"))
    metrics_server = MetricsHTTPServer(metrics_collector, port=port)
    metrics_server.start()

    print(f"Metrics server started on port {port}")
    print(f"Access metrics at: http://localhost:{port}/metrics")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Stop metrics collection when Locust quits"""
    global metrics_server, metrics_collector

    if metrics_server:
        metrics_server.stop()

    if metrics_collector:
        export_path = os.getenv("METRICS_EXPORT_PATH")
        if export_path:
            metrics_collector.export_metrics(export_path)
            print(f"Metrics exported to {export_path}")


class LargeObjectUser(S3Workload):
    """User that performs large object operations"""

    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_size = int(os.getenv("LARGE_OBJECT_SIZE", "100")) * 1024 * 1024
        self.uploaded_keys = []

    @task(3)
    def upload_large_object(self):
        """Upload a large object"""
        key = self.generate_key("large")
        data = self.generate_data(self.object_size)

        start_time = datetime.utcnow()
        success = self.client.upload(key, data)

        if success and metrics_collector:
            metrics_collector.record_operation(
                operation_type=OperationType.WRITE,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data_size_bytes=self.object_size,
                success=True,
            )
            self.uploaded_keys.append(key)

    @task(2)
    def download_large_object(self):
        """Download a large object"""
        if not self.uploaded_keys:
            return

        key = random.choice(self.uploaded_keys)
        start_time = datetime.utcnow()
        data = self.client.download(key)

        if data and metrics_collector:
            metrics_collector.record_operation(
                operation_type=OperationType.READ,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data_size_bytes=len(data),
                success=True,
            )

    @task(1)
    def delete_large_object(self):
        """Delete a large object"""
        if not self.uploaded_keys:
            return

        key = self.uploaded_keys.pop(random.randint(0, len(self.uploaded_keys) - 1))
        start_time = datetime.utcnow()
        success = self.client.delete(key)

        if success and metrics_collector:
            metrics_collector.record_operation(
                operation_type=OperationType.DELETE,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data_size_bytes=0,
                success=True,
            )
