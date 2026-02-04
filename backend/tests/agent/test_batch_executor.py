"""Tests for batch executor."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.batch_executor import (
    BatchActionExecutor,
    StreamingBatchExecutor,
    BatchExecutionConfig,
    BatchExecutionResult,
)


@pytest.fixture
def mock_action_executor():
    """Create a mock ActionExecutor."""
    executor = AsyncMock()

    async def mock_execute(entity_type, action_name, context):
        from app.rule_engine.models import ActionResult
        # Simulate some actions failing
        if "fail" in context.entity.get("id", ""):
            return ActionResult(success=False, error="Simulated failure")
        return ActionResult(success=True, changes={"status": "done"})

    executor.execute = AsyncMock(side_effect=mock_execute)
    return executor


@pytest.fixture
def mock_get_session_func():
    """Create a mock get_session function."""
    async def _get_session():
        session = AsyncMock()
        result = AsyncMock()
        record = MagicMock(props={"name": "Test_001", "status": "draft"})
        result.single = AsyncMock(return_value=record)
        session.run = AsyncMock(return_value=result)
        yield session
    return _get_session


@pytest.fixture
def mock_get_entity_data_func():
    """Create a mock get_entity_data function."""
    async def _get_data(entity_type, entity_id):
        return {"name": entity_id, "status": "draft"}
    return _get_data


class TestBatchExecutionConfig:
    """Test BatchExecutionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BatchExecutionConfig()

        assert config.max_concurrent == 10
        assert config.timeout_per_action == 30
        assert config.retry_on_failure is False
        assert config.max_retries == 1

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BatchExecutionConfig(
            max_concurrent=5,
            timeout_per_action=60,
            retry_on_failure=True,
            max_retries=3
        )

        assert config.max_concurrent == 5
        assert config.timeout_per_action == 60
        assert config.retry_on_failure is True
        assert config.max_retries == 3


class TestBatchExecutionResult:
    """Test BatchExecutionResult dataclass."""

    def test_result_creation(self):
        """Test creating a batch execution result."""
        result = BatchExecutionResult(
            total=10,
            succeeded=8,
            failed=2,
            successes=[
                {"entity_id": "PO_001", "changes": {"status": "submitted"}}
            ],
            failures=[
                {"entity_id": "PO_002", "error": "Precondition failed"}
            ],
            duration_seconds=5.5
        )

        assert result.total == 10
        assert result.succeeded == 8
        assert result.failed == 2
        assert len(result.successes) == 1
        assert len(result.failures) == 1
        assert result.duration_seconds == 5.5


class TestStreamingBatchExecutor:
    """Test StreamingBatchExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_batch_success(self, mock_action_executor, mock_get_session_func, mock_get_entity_data_func):
        """Test successful batch execution."""
        executor = StreamingBatchExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
            get_entity_data_func=mock_get_entity_data_func,
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_001"},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_002"},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_003"},
        ]

        result = await executor.execute_batch(executions)

        assert result.total == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert len(result.successes) == 3
        assert len(result.failures) == 0

    @pytest.mark.asyncio
    async def test_execute_batch_with_failures(self, mock_action_executor, mock_get_session_func, mock_get_entity_data_func):
        """Test batch execution with some failures."""
        executor = StreamingBatchExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
            get_entity_data_func=mock_get_entity_data_func,
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_001"},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_fail_001"},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_002"},
        ]

        result = await executor.execute_batch(executions)

        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        assert len(result.successes) == 2
        assert len(result.failures) == 1
        assert result.failures[0]["entity_id"] == "PO_fail_001"

    @pytest.mark.asyncio
    async def test_execute_batch_with_progress_callback(
        self,
        mock_action_executor,
        mock_get_session_func,
        mock_get_entity_data_func
    ):
        """Test batch execution with progress tracking."""
        progress_updates = []

        async def progress_callback(update):
            progress_updates.append(update)

        executor = StreamingBatchExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
            get_entity_data_func=mock_get_entity_data_func,
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_001"},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_002"},
        ]

        result = await executor.execute_batch(executions, progress_callback=progress_callback)

        # Check that we got progress updates
        assert len(progress_updates) == 2
        assert progress_updates[0]["type"] == "action_progress"
        assert progress_updates[0]["total"] == 2
        assert progress_updates[0]["completed"] in [1, 2]

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, mock_action_executor, mock_get_session_func, mock_get_entity_data_func):
        """Test that concurrency limit is respected."""
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()

        original_execute = mock_action_executor.execute

        async def tracking_execute(entity_type, action_name, context):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent:
                    max_concurrent = concurrent_count
            # Simulate some work
            await asyncio.sleep(0.01)
            async with lock:
                concurrent_count -= 1
            return await original_execute(entity_type, action_name, context)

        mock_action_executor.execute = AsyncMock(side_effect=tracking_execute)

        executor = StreamingBatchExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
            get_entity_data_func=mock_get_entity_data_func,
        )

        # Create many executions
        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": f"PO_{i:03d}"}
            for i in range(20)
        ]

        config = BatchExecutionConfig(max_concurrent=5)
        result = await executor.execute_batch(executions, config=config)

        # Max concurrent should not exceed our limit
        assert max_concurrent <= 5
        assert result.total == 20

    @pytest.mark.asyncio
    async def test_timeout_per_action(self, mock_action_executor, mock_get_session_func, mock_get_entity_data_func):
        """Test timeout per action."""
        # Create a slow executor
        async def slow_execute(entity_type, action_name, context):
            await asyncio.sleep(1)  # Sleep longer than timeout
            from app.rule_engine.models import ActionResult
            return ActionResult(success=True, changes={})

        mock_action_executor.execute = AsyncMock(side_effect=slow_execute)

        executor = StreamingBatchExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
            get_entity_data_func=mock_get_entity_data_func,
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_001"},
        ]

        config = BatchExecutionConfig(timeout_per_action=0.1)  # Short timeout
        result = await executor.execute_batch(executions, config=config)

        # Should fail due to timeout
        assert result.total == 1
        assert result.failed == 1
        assert "Timeout" in result.failures[0]["error"]


class TestBatchActionExecutor:
    """Test BatchActionExecutor alias class."""

    def test_is_subclass_of_streaming_executor(self):
        """Test that BatchActionExecutor is a subclass of StreamingBatchExecutor."""
        assert issubclass(BatchActionExecutor, StreamingBatchExecutor)

    def test_instantiation(self, mock_action_executor, mock_get_session_func):
        """Test that BatchActionExecutor can be instantiated."""
        executor = BatchActionExecutor(
            action_executor=mock_action_executor,
            get_session_func=mock_get_session_func,
        )

        assert isinstance(executor, StreamingBatchExecutor)
