"""S3 Read Overload Scenario - Simulates release day traffic with heavy read load"""

import random
from datetime import datetime
from locust import task, between, events
import uuid
import yaml

from chopsticks.workloads.s3.s3_workload import S3Workload
from chopsticks.metrics import (
    MetricsCollector,
    TestConfiguration,
    OperationType,
    WorkloadType,
)
from chopsticks.metrics.http_server import MetricsHTTPServer


# Global state
metrics_server = None
metrics_collector = None
test_config = None
scenario_config = None
s3_config = None
test_objects: dict[str, list[tuple[str, int]]] = {
    "small": [],
    "medium": [],
    "large": [],
}


def load_s3_config():
    """Load S3 workload configuration from YAML file"""
    with open("config/s3_config.yaml", "r") as f:
        config = yaml.safe_load(f)

    required_fields = [
        "endpoint",
        "access_key",
        "secret_key",
        "bucket",
        "region",
        "driver",
    ]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required S3 configuration field: {field}")

    return config


def load_scenario_config():
    """Load scenario-specific configuration from YAML file"""
    with open("config/scenarios/s3_read_overload.yaml", "r") as f:
        config = yaml.safe_load(f)

    required_fields = [
        "num_small_objects",
        "num_medium_objects",
        "num_large_objects",
        "small_object_size_kb",
        "medium_object_size_kb",
        "large_object_size_mb",
        "read_weight_small",
        "read_weight_medium",
        "read_weight_large",
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required scenario configuration field: {field}")

    return config


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize metrics collection when Locust starts"""
    global metrics_server, metrics_collector, test_config, scenario_config, s3_config

    # Load configurations
    s3_config = load_s3_config()
    scenario_config = load_scenario_config()

    # Create test configuration
    test_config = TestConfiguration(
        test_run_id=str(uuid.uuid4()),
        test_name="S3 Read Overload",
        start_time=datetime.utcnow(),
        scenario="s3_read_overload",
        workload_type=WorkloadType.S3,
        test_config={
            "num_small_objects": scenario_config["num_small_objects"],
            "num_medium_objects": scenario_config["num_medium_objects"],
            "num_large_objects": scenario_config["num_large_objects"],
            "small_object_size_kb": scenario_config["small_object_size_kb"],
            "medium_object_size_kb": scenario_config["medium_object_size_kb"],
            "large_object_size_mb": scenario_config["large_object_size_mb"],
            "read_weight_small": scenario_config["read_weight_small"],
            "read_weight_medium": scenario_config["read_weight_medium"],
            "read_weight_large": scenario_config["read_weight_large"],
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

    # Start HTTP metrics server
    metrics_server = MetricsHTTPServer(metrics_collector, port=9090)
    metrics_server.start()

    print(f"\n{'=' * 80}")
    print("Read Overload Test Configuration:")
    print(f"  Test Run ID: {test_config.test_run_id}")
    print(
        f"  Small Objects: {scenario_config['num_small_objects']} x {scenario_config['small_object_size_kb']}KB"
    )
    print(
        f"  Medium Objects: {scenario_config['num_medium_objects']} x {scenario_config['medium_object_size_kb']}KB"
    )
    print(
        f"  Large Objects: {scenario_config['num_large_objects']} x {scenario_config['large_object_size_mb']}MB"
    )
    print(
        f"  Read Weights: Small={scenario_config['read_weight_small']}%, Medium={scenario_config['read_weight_medium']}%, Large={scenario_config['read_weight_large']}%"
    )
    print("  Metrics Server: http://localhost:9090/metrics")
    print(f"{'=' * 80}\n")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup phase: Upload objects of various sizes before test starts"""
    global test_objects, metrics_collector, s3_config, scenario_config

    print(f"\n{'=' * 80}")
    print("SETUP PHASE: Uploading test objects...")
    print(f"{'=' * 80}\n")

    # Create S3Workload instance for setup
    workload = S3Workload(
        endpoint=s3_config["endpoint"],
        access_key=s3_config["access_key"],
        secret_key=s3_config["secret_key"],
        bucket=s3_config["bucket"],
        region=s3_config["region"],
        client_type=s3_config["driver"],
    )

    # Upload small objects
    print(
        f"Uploading {scenario_config['num_small_objects']} small objects ({scenario_config['small_object_size_kb']}KB each)..."
    )
    size_bytes = scenario_config["small_object_size_kb"] * 1024
    for i in range(scenario_config["num_small_objects"]):
        key = f"read-overload/small/{uuid.uuid4()}.bin"
        data = b"x" * size_bytes

        start_time = datetime.utcnow()
        success = workload.put_object(key, data)
        end_time = datetime.utcnow()

        if success:
            test_objects["small"].append((key, size_bytes))
            metrics_collector.record_operation(
                OperationType.UPLOAD, key, size_bytes, start_time, end_time, True
            )
        else:
            metrics_collector.record_operation(
                OperationType.UPLOAD,
                key,
                size_bytes,
                start_time,
                end_time,
                False,
                "Upload failed",
            )

    print(f"✓ Uploaded {len(test_objects['small'])} small objects")

    # Upload medium objects
    print(
        f"Uploading {scenario_config['num_medium_objects']} medium objects ({scenario_config['medium_object_size_kb']}KB each)..."
    )
    size_bytes = scenario_config["medium_object_size_kb"] * 1024
    for i in range(scenario_config["num_medium_objects"]):
        key = f"read-overload/medium/{uuid.uuid4()}.bin"
        data = b"x" * size_bytes

        start_time = datetime.utcnow()
        success = workload.put_object(key, data)
        end_time = datetime.utcnow()

        if success:
            test_objects["medium"].append((key, size_bytes))
            metrics_collector.record_operation(
                OperationType.UPLOAD, key, size_bytes, start_time, end_time, True
            )
        else:
            metrics_collector.record_operation(
                OperationType.UPLOAD,
                key,
                size_bytes,
                start_time,
                end_time,
                False,
                "Upload failed",
            )

    print(f"✓ Uploaded {len(test_objects['medium'])} medium objects")

    # Upload large objects
    print(
        f"Uploading {scenario_config['num_large_objects']} large objects ({scenario_config['large_object_size_mb']}MB each)..."
    )
    size_bytes = scenario_config["large_object_size_mb"] * 1024 * 1024
    for i in range(scenario_config["num_large_objects"]):
        key = f"read-overload/large/{uuid.uuid4()}.bin"
        data = b"x" * size_bytes

        start_time = datetime.utcnow()
        success = workload.put_object(key, data)
        end_time = datetime.utcnow()

        if success:
            test_objects["large"].append((key, size_bytes))
            metrics_collector.record_operation(
                OperationType.UPLOAD, key, size_bytes, start_time, end_time, True
            )
        else:
            metrics_collector.record_operation(
                OperationType.UPLOAD,
                key,
                size_bytes,
                start_time,
                end_time,
                False,
                "Upload failed",
            )

    print(f"✓ Uploaded {len(test_objects['large'])} large objects")

    total_objects = (
        len(test_objects["small"])
        + len(test_objects["medium"])
        + len(test_objects["large"])
    )
    print(f"\n{'=' * 80}")
    print(f"SETUP COMPLETE: {total_objects} objects ready for read overload test")
    print(f"{'=' * 80}\n")


@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Cleanup when Locust quits"""
    global metrics_server, metrics_collector, test_config

    if metrics_server:
        metrics_server.stop()

    if metrics_collector:
        # Export final metrics
        summary = metrics_collector.get_summary()
        report_path = f"read_overload_report_{test_config.test_run_id}.json"
        metrics_collector.export_to_json(report_path)

        print(f"\n{'=' * 80}")
        print("Test Summary:")
        print(f"  Total Operations: {summary['total_operations']}")
        print(f"  Success Rate: {summary['success_rate']:.2f}%")
        print(f"  Average Latency: {summary['avg_latency_ms']:.2f}ms")
        print(f"  Total Throughput: {summary['total_throughput_mbps']:.2f} MB/s")
        print(f"  Report saved to: {report_path}")
        print(f"{'=' * 80}\n")


class S3ReadOverloadUser(S3Workload):
    """Locust user that performs read-heavy operations simulating release day traffic"""

    wait_time = between(0.1, 0.5)  # Fast-paced reads

    def __init__(self, *args, **kwargs):
        # Initialize S3Workload with configuration
        if s3_config is None:
            raise RuntimeError(
                "S3 configuration not loaded. Did Locust initialization fail?"
            )

        super().__init__(
            endpoint=s3_config["endpoint"],
            access_key=s3_config["access_key"],
            secret_key=s3_config["secret_key"],
            bucket=s3_config["bucket"],
            region=s3_config["region"],
            client_type=s3_config["driver"],
        )

        # Build weighted choices for object selection
        self.object_pool = []
        self.object_pool.extend(
            [("small", obj) for obj in test_objects["small"]]
            * scenario_config["read_weight_small"]
        )
        self.object_pool.extend(
            [("medium", obj) for obj in test_objects["medium"]]
            * scenario_config["read_weight_medium"]
        )
        self.object_pool.extend(
            [("large", obj) for obj in test_objects["large"]]
            * scenario_config["read_weight_large"]
        )

        if not self.object_pool:
            raise RuntimeError(
                "No test objects available. Setup phase may have failed."
            )

    @task
    def read_object(self):
        """Read a random object based on configured weights"""
        # Select random object based on weights
        category, (key, size_bytes) = random.choice(self.object_pool)

        start_time = datetime.utcnow()
        data = self.get_object(key)
        end_time = datetime.utcnow()

        success = data is not None
        error_message = None if success else "Download failed"

        # Record metrics
        metrics_collector.record_operation(
            OperationType.DOWNLOAD,
            key,
            size_bytes if success else 0,
            start_time,
            end_time,
            success,
            error_message,
        )

        # Report to Locust
        latency_ms = (end_time - start_time).total_seconds() * 1000
        if success:
            self.environment.events.request.fire(
                request_type="S3",
                name=f"GET /{category}",
                response_time=latency_ms,
                response_length=size_bytes,
                exception=None,
                context={},
            )
        else:
            self.environment.events.request.fire(
                request_type="S3",
                name=f"GET /{category}",
                response_time=latency_ms,
                response_length=0,
                exception=Exception(error_message),
                context={},
            )
