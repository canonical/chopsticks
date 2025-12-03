"""S3 Metadata-Intensive Stress Test"""

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
    """Initialize metrics collection"""
    global metrics_server, metrics_collector, test_config

    test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name="S3 Metadata Intensive",
        start_time=datetime.utcnow(),
        scenario="metadata_intensive",
        workload_type=WorkloadType.S3,
        test_config={
            "object_count": 10000,
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


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Stop metrics collection"""
    global metrics_server, metrics_collector

    if metrics_server:
        metrics_server.stop()

    if metrics_collector:
        export_path = os.getenv("METRICS_EXPORT_PATH")
        if export_path:
            metrics_collector.export_metrics(export_path)


class MetadataIntensiveUser(S3Workload):
    """User that performs metadata-heavy operations"""

    wait_time = between(0.1, 0.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.small_object_size = 1024  # 1KB
        self.uploaded_keys = []

    @task(2)
    def list_objects(self):
        """List objects in bucket"""
        start_time = datetime.utcnow()
        keys = self.client.list_objects(prefix="metadata", max_keys=1000)

        if metrics_collector:
            metrics_collector.record_operation(
                operation_type=OperationType.METADATA,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data_size_bytes=0,
                success=True,
            )

    @task(3)
    def head_object(self):
        """Get object metadata"""
        if not self.uploaded_keys:
            return

        key = random.choice(self.uploaded_keys)
        start_time = datetime.utcnow()
        metadata = self.client.head_object(key)

        if metadata and metrics_collector:
            metrics_collector.record_operation(
                operation_type=OperationType.METADATA,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data_size_bytes=0,
                success=True,
            )

    @task(1)
    def upload_small_object(self):
        """Upload small object to populate bucket"""
        key = self.generate_key("metadata")
        data = self.generate_data(self.small_object_size)

        start_time = datetime.utcnow()
        success = self.client.upload(key, data, metadata={"test": "metadata"})

        if success:
            self.uploaded_keys.append(key)
            if metrics_collector:
                metrics_collector.record_operation(
                    operation_type=OperationType.WRITE,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    data_size_bytes=self.small_object_size,
                    success=True,
                )
