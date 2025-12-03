"""S3 Versioning Workload Test"""

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
        test_name="S3 Versioning Workload",
        start_time=datetime.utcnow(),
        scenario="versioning_workload",
        workload_type=WorkloadType.S3,
        test_config={
            "versions_per_object": 10,
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


class VersioningWorkloadUser(S3Workload):
    """User that creates multiple versions of objects"""

    wait_time = between(0.5, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_size = 10 * 1024  # 10KB
        self.object_keys = {}  # key -> version_count

    @task(5)
    def create_new_version(self):
        """Upload new version of existing object"""
        if not self.object_keys:
            # Create first version
            key = self.generate_key("versioned")
            self.object_keys[key] = 0

        # Pick random key or create new one
        if random.random() < 0.3 or not self.object_keys:
            key = self.generate_key("versioned")
            self.object_keys[key] = 0
        else:
            key = random.choice(list(self.object_keys.keys()))

        data = self.generate_data(self.object_size)
        start_time = datetime.utcnow()
        success = self.client.upload(key, data)

        if success:
            self.object_keys[key] += 1
            if metrics_collector:
                metrics_collector.record_operation(
                    operation_type=OperationType.WRITE,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    data_size_bytes=self.object_size,
                    success=True,
                )

    @task(3)
    def read_latest_version(self):
        """Read latest version of object"""
        if not self.object_keys:
            return

        key = random.choice(list(self.object_keys.keys()))
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
    def delete_object(self):
        """Delete object (creates delete marker in versioned bucket)"""
        if not self.object_keys or len(self.object_keys) < 5:
            return

        key = random.choice(list(self.object_keys.keys()))
        start_time = datetime.utcnow()
        success = self.client.delete(key)

        if success:
            del self.object_keys[key]
            if metrics_collector:
                metrics_collector.record_operation(
                    operation_type=OperationType.DELETE,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    data_size_bytes=0,
                    success=True,
                )
