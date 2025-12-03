"""Tests for S3 Read Overload scenario"""

import os
import pytest
from unittest.mock import Mock, patch

from chopsticks.scenarios.s3_read_overload import S3ReadOverloadUser


@pytest.fixture
def mock_environment():
    """Create a mock Locust environment"""
    env = Mock()
    env.parsed_options = Mock()
    env.parsed_options.num_users = 10
    return env


@pytest.fixture
def s3_read_overload_user():
    """Create S3ReadOverloadUser instance with mocked dependencies"""
    with patch.dict(
        os.environ,
        {
            "S3_ENDPOINT": "http://test-endpoint:9000",
            "S3_ACCESS_KEY": "test-access",
            "S3_SECRET_KEY": "test-secret",
            "S3_BUCKET": "test-bucket",
            "S3_REGION": "us-east-1",
            "S3_CLIENT_TYPE": "s5cmd",
        },
    ):
        # Mock the driver initialization and Locust User
        with patch(
            "chopsticks.workloads.s3.s3_workload.S5cmdDriver"
        ) as mock_driver_class:
            with patch("locust.User.__init__", return_value=None):
                mock_driver = Mock()
                mock_driver_class.return_value = mock_driver

                user = S3ReadOverloadUser(Mock())
                user.driver = mock_driver
                return user


class TestS3ReadOverloadUser:
    """Test cases for S3ReadOverloadUser"""

    def test_initialization(self, s3_read_overload_user):
        """Test that user initializes with mocked driver"""
        assert s3_read_overload_user.driver is not None

    def test_select_object_weighted_empty_list(self, s3_read_overload_user):
        """Test object selection with empty list"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = []
        result = s3_read_overload_user._select_object_weighted()
        assert result is None

    def test_select_object_weighted_single_object(self, s3_read_overload_user):
        """Test object selection with single object"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = [{"key": "test-key", "size_bytes": 1024}]
        result = s3_read_overload_user._select_object_weighted()
        assert result is not None
        assert result["key"] == "test-key"

    def test_select_object_weighted_distribution(self, s3_read_overload_user):
        """Test that smaller objects are selected more frequently"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        # Create objects with varying sizes
        scenario_module.test_objects = [
            {"key": f"small-{i}", "size_bytes": 1024 * (i + 1)}
            for i in range(10)  # 1KB to 10KB
        ] + [
            {"key": f"large-{i}", "size_bytes": 1024 * 1024 * (i + 1)}
            for i in range(10)  # 1MB to 10MB
        ]

        # Sample multiple selections
        selections = [
            s3_read_overload_user._select_object_weighted() for _ in range(100)
        ]

        # Count small vs large selections
        small_count = sum(1 for s in selections if "small" in s["key"])
        large_count = sum(1 for s in selections if "large" in s["key"])

        # Small objects should be selected significantly more often
        # With 80/20 weighting, we expect roughly 80% small, 20% large
        # Allow some variance (60-95% for small objects due to randomness)
        assert small_count > large_count
        assert 60 <= small_count <= 95  # Allow for randomness

    @patch("chopsticks.scenarios.s3_read_overload.events")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_download_object_success(
        self, mock_collector, mock_events, s3_read_overload_user
    ):
        """Test successful object download"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = [{"key": "test-key", "size_bytes": 1024}]

        # Mock successful download
        test_data = b"x" * 1024
        s3_read_overload_user.get_object = Mock(return_value=test_data)

        # Execute download
        s3_read_overload_user.download_object()

        # Verify get_object was called
        s3_read_overload_user.get_object.assert_called_once_with("test-key")

        # Verify metrics were recorded
        assert mock_collector.record_operation.called
        metric = mock_collector.record_operation.call_args[0][0]
        assert metric.success is True
        assert metric.object_size_bytes == 1024

        # Verify Locust event was fired
        assert mock_events.request.fire.called

    @patch("chopsticks.scenarios.s3_read_overload.events")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_download_object_failure(
        self, mock_collector, mock_events, s3_read_overload_user
    ):
        """Test failed object download"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = [{"key": "test-key", "size_bytes": 1024}]

        # Mock failed download
        s3_read_overload_user.get_object = Mock(return_value=None)

        # Execute download
        s3_read_overload_user.download_object()

        # Verify metrics were recorded with failure
        assert mock_collector.record_operation.called
        metric = mock_collector.record_operation.call_args[0][0]
        assert metric.success is False
        assert metric.error_message is not None

        # Verify Locust event was fired with exception
        assert mock_events.request.fire.called
        call_kwargs = mock_events.request.fire.call_args[1]
        assert call_kwargs["exception"] is not None

    @patch("chopsticks.scenarios.s3_read_overload.events")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_download_object_size_mismatch(
        self, mock_collector, mock_events, s3_read_overload_user
    ):
        """Test object download with size mismatch"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = [{"key": "test-key", "size_bytes": 1024}]

        # Mock download with wrong size
        test_data = b"x" * 512  # Expected 1024, got 512
        s3_read_overload_user.get_object = Mock(return_value=test_data)

        # Execute download
        s3_read_overload_user.download_object()

        # Verify metrics were recorded with failure
        assert mock_collector.record_operation.called
        metric = mock_collector.record_operation.call_args[0][0]
        assert metric.success is False
        assert "Size mismatch" in metric.error_message

    @patch("chopsticks.scenarios.s3_read_overload.events")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_list_objects_success(
        self, mock_collector, mock_events, s3_read_overload_user
    ):
        """Test successful list objects operation"""
        # Mock successful list
        test_objects = ["key1", "key2", "key3"]
        s3_read_overload_user.list_objects_api = Mock(return_value=test_objects)

        # Execute list
        s3_read_overload_user.list_objects()

        # Verify list was called
        s3_read_overload_user.list_objects_api.assert_called_once()

        # Verify metrics were recorded
        assert mock_collector.record_operation.called
        metric = mock_collector.record_operation.call_args[0][0]
        assert metric.success is True
        assert metric.metadata["object_count"] == 3

        # Verify Locust event was fired
        assert mock_events.request.fire.called

    @patch("chopsticks.scenarios.s3_read_overload.events")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_list_objects_failure(
        self, mock_collector, mock_events, s3_read_overload_user
    ):
        """Test failed list objects operation"""
        # Mock failed list
        s3_read_overload_user.list_objects_api = Mock(return_value=None)

        # Execute list
        s3_read_overload_user.list_objects()

        # Verify metrics were recorded with failure
        assert mock_collector.record_operation.called
        metric = mock_collector.record_operation.call_args[0][0]
        assert metric.success is False

        # Verify Locust event was fired with exception
        assert mock_events.request.fire.called
        call_kwargs = mock_events.request.fire.call_args[1]
        assert call_kwargs["exception"] is not None

    def test_download_no_objects(self, s3_read_overload_user):
        """Test download when no test objects are available"""
        import chopsticks.scenarios.s3_read_overload as scenario_module

        scenario_module.test_objects = []

        # Should return early without error
        s3_read_overload_user.download_object()


class TestScenarioLifecycle:
    """Test scenario lifecycle events"""

    @patch("chopsticks.scenarios.s3_read_overload.MetricsHTTPServer")
    @patch("chopsticks.scenarios.s3_read_overload.MetricsCollector")
    def test_on_locust_init(
        self, mock_collector_class, mock_server_class, mock_environment
    ):
        """Test initialization event handler"""
        from chopsticks.scenarios.s3_read_overload import on_locust_init

        with patch.dict(
            os.environ, {"METRICS_PORT": "9999", "NUM_OBJECTS": "50"}, clear=True
        ):
            # Call init handler
            on_locust_init(mock_environment)

            # Verify metrics collector was initialized
            assert mock_collector_class.called

            # Verify metrics server was started
            assert mock_server_class.called
            mock_server = mock_server_class.return_value
            mock_server.start.assert_called_once()

    @patch("chopsticks.scenarios.s3_read_overload.S3Workload")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_on_test_start_upload_success(self, mock_collector, mock_workload_class):
        """Test setup phase with successful uploads"""
        from chopsticks.scenarios.s3_read_overload import on_test_start
        import chopsticks.scenarios.s3_read_overload as scenario_module

        # Reset test objects
        scenario_module.test_objects = []

        # Mock workload
        mock_workload = Mock()
        mock_workload.put_object = Mock(return_value=True)
        mock_workload_class.return_value = mock_workload

        with patch.dict(os.environ, {"NUM_OBJECTS": "5"}, clear=True):
            # Call test start handler
            on_test_start(Mock())

            # Verify objects were uploaded
            assert len(scenario_module.test_objects) == 5
            assert mock_workload.put_object.call_count == 5

            # Verify metrics were recorded
            assert mock_collector.record_operation.call_count == 5

    @patch("chopsticks.scenarios.s3_read_overload.S3Workload")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    def test_on_test_start_upload_failure(self, mock_collector, mock_workload_class):
        """Test setup phase with upload failures"""
        from chopsticks.scenarios.s3_read_overload import on_test_start
        import chopsticks.scenarios.s3_read_overload as scenario_module

        # Reset test objects
        scenario_module.test_objects = []

        # Mock workload with failures
        mock_workload = Mock()
        mock_workload.put_object = Mock(return_value=False)
        mock_workload_class.return_value = mock_workload

        with patch.dict(os.environ, {"NUM_OBJECTS": "3"}, clear=True):
            # Call test start handler
            on_test_start(Mock())

            # Verify no objects were added to test list
            assert len(scenario_module.test_objects) == 0

            # Verify failure metrics were recorded
            assert mock_collector.record_operation.call_count == 3
            for call in mock_collector.record_operation.call_args_list:
                metric = call[0][0]
                assert metric.success is False

    @patch("chopsticks.scenarios.s3_read_overload.S3Workload")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_collector")
    @patch("chopsticks.scenarios.s3_read_overload.metrics_server")
    def test_on_test_stop_cleanup(
        self, mock_server, mock_collector, mock_workload_class
    ):
        """Test cleanup phase"""
        from chopsticks.scenarios.s3_read_overload import on_test_stop
        import chopsticks.scenarios.s3_read_overload as scenario_module

        # Setup test objects
        scenario_module.test_objects = [
            {"key": "test-1", "size_bytes": 1024},
            {"key": "test-2", "size_bytes": 2048},
        ]

        # Mock workload
        mock_workload = Mock()
        mock_workload.delete_object = Mock(return_value=True)
        mock_workload_class.return_value = mock_workload

        # Call test stop handler
        on_test_stop(Mock())

        # Verify objects were deleted
        assert mock_workload.delete_object.call_count == 2

        # Verify metrics were finalized
        mock_collector.finalize.assert_called_once()

        # Verify server was stopped
        mock_server.stop.assert_called_once()
