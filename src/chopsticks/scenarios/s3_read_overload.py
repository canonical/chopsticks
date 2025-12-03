"""S3 Read Overload Stress Test - Simulates Release Day Traffic Surge"""

import os
import random
from datetime import datetime
from locust import task, between, events
import uuid

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics import (
    MetricsCollector,
    TestConfiguration,
    OperationMetric,
    OperationType,
    WorkloadType,
)
from chopsticks.metrics.http_server import MetricsHTTPServer


# Global metrics server and collector
metrics_server = None
metrics_collector = None
test_config = None
test_objects = []


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collection when Locust starts"""
    global metrics_server, metrics_collector, test_config

    # Create test configuration
    test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name="S3 Read Overload - Release Day Simulation",
        start_time=datetime.utcnow(),
        scenario="s3_read_overload",
        workload_type=WorkloadType.S3,
        test_config={
            "min_object_size_kb": int(os.getenv("MIN_OBJECT_SIZE_KB", "1")),
            "max_object_size_mb": int(os.getenv("MAX_OBJECT_SIZE_MB", "25")),
            "num_objects": int(os.getenv("NUM_OBJECTS", "100")),
            "users": environment.parsed_options.num_users
            if hasattr(environment, "parsed_options")
            else 1,
        },
    )

    # Initialize metrics collector
    metrics_collector = MetricsCollector(
        test_run_id=test_config.test_run_id,
        test_config=test_config,
        aggregation_window_seconds=10,
    )

    # Start metrics HTTP server
    metrics_port = int(os.getenv("METRICS_PORT", "9090"))
    metrics_server = MetricsHTTPServer(
        collector=metrics_collector, port=metrics_port, host="0.0.0.0"
    )
    metrics_server.start()
    print(f"Metrics server started on http://0.0.0.0:{metrics_port}/metrics")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup phase: Upload objects of various sizes before test starts"""
    global test_objects, metrics_collector

    print("=" * 80)
    print("SETUP PHASE: Uploading test objects...")
    print("=" * 80)

    min_size_kb = int(os.getenv("MIN_OBJECT_SIZE_KB", "1"))
    max_size_mb = int(os.getenv("MAX_OBJECT_SIZE_MB", "25"))
    num_objects = int(os.getenv("NUM_OBJECTS", "100"))
    bucket = os.getenv("S3_BUCKET", "chopsticks-test")

    # Create a temporary S3Workload instance for setup
    setup_workload = S3Workload(
        endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        bucket=bucket,
        region=os.getenv("S3_REGION", "us-east-1"),
        client_type=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
    )

    # Define object size distribution
    # 40% small (1KB - 100KB)
    # 30% medium (100KB - 1MB)
    # 20% large (1MB - 10MB)
    # 10% very large (10MB - 25MB)
    size_ranges = [
        (1, 100, 0.4),  # KB range, probability
        (100, 1024, 0.3),  # KB range
        (1024, 10240, 0.2),  # KB range
        (10240, max_size_mb * 1024, 0.1),  # KB range
    ]

    uploaded_count = 0
    failed_count = 0

    for i in range(num_objects):
        # Select size range based on probability
        rand = random.random()
        cumulative = 0
        selected_range = size_ranges[0]

        for size_range in size_ranges:
            cumulative += size_range[2]
            if rand <= cumulative:
                selected_range = size_range
                break

        # Generate random size within selected range
        size_kb = random.randint(
            max(min_size_kb, int(selected_range[0])), int(selected_range[1])
        )
        size_bytes = size_kb * 1024

        # Generate unique object key
        key = f"read-overload-test-{uuid.uuid4()}-{size_kb}kb"

        # Generate random data
        data = os.urandom(size_bytes)

        # Upload object
        start_time = datetime.utcnow()
        success = setup_workload.put_object(key, data)
        end_time = datetime.utcnow()

        if success:
            test_objects.append({"key": key, "size_bytes": size_bytes})
            uploaded_count += 1

            # Record setup metrics
            if metrics_collector:
                duration_ms = (end_time - start_time).total_seconds() * 1000
                throughput_mbps = (
                    (size_bytes / 1024 / 1024) / (duration_ms / 1000)
                    if duration_ms > 0
                    else 0
                )

                metric = OperationMetric(
                    operation_id=str(uuid.uuid4()),
                    timestamp_start=start_time,
                    timestamp_end=end_time,
                    operation_type=OperationType.UPLOAD,
                    workload_type=WorkloadType.S3,
                    object_key=key,
                    object_size_bytes=size_bytes,
                    duration_ms=duration_ms,
                    throughput_mbps=throughput_mbps,
                    success=True,
                    driver=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
                    metadata={"phase": "setup"},
                )
                metrics_collector.record_operation(metric)

            if (i + 1) % 10 == 0:
                print(f"Uploaded {uploaded_count}/{num_objects} objects...")
        else:
            failed_count += 1
            print(f"Failed to upload object {key}")

            # Record failed setup metric
            if metrics_collector:
                duration_ms = (end_time - start_time).total_seconds() * 1000

                metric = OperationMetric(
                    operation_id=str(uuid.uuid4()),
                    timestamp_start=start_time,
                    timestamp_end=end_time,
                    operation_type=OperationType.UPLOAD,
                    workload_type=WorkloadType.S3,
                    object_key=key,
                    object_size_bytes=size_bytes,
                    duration_ms=duration_ms,
                    throughput_mbps=0,
                    success=False,
                    error_message="Upload failed during setup",
                    driver=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
                    metadata={"phase": "setup"},
                )
                metrics_collector.record_operation(metric)

    print("=" * 80)
    print(f"SETUP COMPLETE: {uploaded_count} objects uploaded, {failed_count} failed")
    print(f"Test objects ready: {len(test_objects)}")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Cleanup phase: Remove test objects and finalize metrics"""
    global test_objects, metrics_collector, metrics_server

    print("=" * 80)
    print("CLEANUP PHASE: Removing test objects...")
    print("=" * 80)

    bucket = os.getenv("S3_BUCKET", "chopsticks-test")

    # Create a temporary S3Workload instance for cleanup
    cleanup_workload = S3Workload(
        endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
        bucket=bucket,
        region=os.getenv("S3_REGION", "us-east-1"),
        client_type=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
    )

    deleted_count = 0
    failed_count = 0

    for obj in test_objects:
        if cleanup_workload.delete_object(obj["key"]):
            deleted_count += 1
        else:
            failed_count += 1
            print(f"Failed to delete object {obj['key']}")

    print("=" * 80)
    print(f"CLEANUP COMPLETE: {deleted_count} objects deleted, {failed_count} failed")
    print("=" * 80)

    # Finalize metrics
    if metrics_collector:
        metrics_collector.finalize()
        print("\nMetrics collection finalized")

    # Stop metrics server
    if metrics_server:
        metrics_server.stop()
        print("Metrics server stopped")


class S3ReadOverloadUser(S3Workload):
    """
    S3 User simulating release day read overload.

    This scenario focuses on saturating read throughput by continuously
    downloading objects of various sizes. The read pattern is weighted
    to simulate realistic access patterns where smaller files are accessed
    more frequently than larger ones.
    """

    # Wait between 0.1 and 0.5 seconds between requests to generate high load
    wait_time = between(0.1, 0.5)

    def __init__(self, *args, **kwargs):
        """Initialize S3 workload with configuration from environment"""
        super().__init__(
            endpoint=os.getenv("S3_ENDPOINT", "http://localhost:9000"),
            access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
            bucket=os.getenv("S3_BUCKET", "chopsticks-test"),
            region=os.getenv("S3_REGION", "us-east-1"),
            client_type=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
        )

    def _select_object_weighted(self):
        """
        Select an object with weighted probability based on size.
        Smaller objects are accessed more frequently (80% of the time).
        """
        if not test_objects:
            return None

        # 80% chance to select from smaller half of objects
        if random.random() < 0.8:
            # Sort by size and get smaller half
            sorted_objects = sorted(test_objects, key=lambda x: x["size_bytes"])
            smaller_half = sorted_objects[: len(sorted_objects) // 2]
            return random.choice(smaller_half) if smaller_half else random.choice(
                test_objects
            )
        else:
            # 20% chance to select any object
            return random.choice(test_objects)

    @task(100)
    def download_object(self):
        """Download a random object with weighted selection"""
        global metrics_collector

        if not test_objects:
            print("No test objects available for download")
            return

        # Select object with weighted probability
        obj = self._select_object_weighted()
        if not obj:
            return

        key = obj["key"]
        expected_size = obj["size_bytes"]

        # Download object
        start_time = datetime.utcnow()
        data = self.get_object(key)
        end_time = datetime.utcnow()

        success = data is not None and len(data) == expected_size
        error_message = None

        if data is None:
            error_message = "Download failed - no data returned"
        elif len(data) != expected_size:
            error_message = (
                f"Size mismatch: expected {expected_size}, got {len(data)}"
            )

        # Record metrics
        if metrics_collector:
            duration_ms = (end_time - start_time).total_seconds() * 1000
            size = len(data) if data else 0
            throughput_mbps = (
                (size / 1024 / 1024) / (duration_ms / 1000) if duration_ms > 0 else 0
            )

            metric = OperationMetric(
                operation_id=str(uuid.uuid4()),
                timestamp_start=start_time,
                timestamp_end=end_time,
                operation_type=OperationType.DOWNLOAD,
                workload_type=WorkloadType.S3,
                object_key=key,
                object_size_bytes=size,
                duration_ms=duration_ms,
                throughput_mbps=throughput_mbps,
                success=success,
                error_message=error_message,
                driver=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
            )
            metrics_collector.record_operation(metric)

        # Report to Locust
        duration = (end_time - start_time).total_seconds() * 1000
        if success:
            events.request.fire(
                request_type="S3_GET",
                name=f"download_{expected_size // 1024}kb",
                response_time=duration,
                response_length=len(data),
                exception=None,
            )
        else:
            events.request.fire(
                request_type="S3_GET",
                name=f"download_{expected_size // 1024}kb",
                response_time=duration,
                response_length=0,
                exception=Exception(error_message or "Download failed"),
            )

    @task(5)
    def list_objects(self):
        """Occasionally list objects to simulate realistic access patterns"""
        global metrics_collector

        start_time = datetime.utcnow()
        objects = self.list_objects_api()
        end_time = datetime.utcnow()

        success = objects is not None

        # Record metrics
        if metrics_collector:
            duration_ms = (end_time - start_time).total_seconds() * 1000

            metric = OperationMetric(
                operation_id=str(uuid.uuid4()),
                timestamp_start=start_time,
                timestamp_end=end_time,
                operation_type=OperationType.LIST,
                workload_type=WorkloadType.S3,
                object_key="",
                object_size_bytes=0,
                duration_ms=duration_ms,
                throughput_mbps=0,
                success=success,
                driver=os.getenv("S3_CLIENT_TYPE", "s5cmd"),
                metadata={"object_count": len(objects) if objects else 0},
            )
            metrics_collector.record_operation(metric)

        # Report to Locust
        duration = (end_time - start_time).total_seconds() * 1000
        if success:
            events.request.fire(
                request_type="S3_LIST",
                name="list_objects",
                response_time=duration,
                response_length=len(objects) if objects else 0,
                exception=None,
            )
        else:
            events.request.fire(
                request_type="S3_LIST",
                name="list_objects",
                response_time=duration,
                response_length=0,
                exception=Exception("List failed"),
            )
