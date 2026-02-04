"""End-to-end tests for the enhanced agent system.

These tests simulate real user scenarios with mocked external dependencies.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from langchain_openai import ChatOpenAI

from app.services.agent import EnhancedAgentService
from app.services.agent.state import UserIntent
from app.rule_engine.models import ActionDef, Parameter, Precondition, ActionResult
from app.rule_engine.action_executor import ActionExecutor
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.context import EvaluationContext


@pytest.fixture
def llm_config():
    """Test LLM configuration."""
    return {
        "api_key": "test-key",
        "base_url": "https://api.test.com",
        "model": "gpt-4",
    }


@pytest.fixture
def neo4j_config():
    """Test Neo4j configuration."""
    return {
        "uri": "bolt://localhost:7687",
        "username": "neo4j",
        "password": "password",
        "database": "neo4j",
    }


@pytest.fixture
def sample_action_registry():
    """Create a registry with sample actions for testing."""
    registry = ActionRegistry()

    # Register submit action for PurchaseOrder
    submit_action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[Parameter(name="confirm", param_type="boolean", optional=True)],
        preconditions=[
            Precondition(
                name="is_draft",
                condition={"type": "property", "property": "status", "op": "==", "value": "draft"},
                on_failure="订单必须是草稿状态"
            )
        ],
        effect={"type": "set", "property": "status", "value": "submitted"}
    )
    registry.register(submit_action)

    # Register pay action for Invoice
    pay_action = ActionDef(
        entity_type="Invoice",
        action_name="pay",
        parameters=[Parameter(name="amount", param_type="decimal", optional=True)],
        preconditions=[
            Precondition(
                name="is_unpaid",
                condition={"type": "property", "property": "status", "op": "!=", "value": "paid"},
                on_failure="发票已支付"
            )
        ],
        effect={"type": "set", "property": "status", "value": "paid"}
    )
    registry.register(pay_action)

    return registry


@pytest.fixture
def sample_action_executor():
    """Create a mock action executor with realistic behavior."""
    # Create executor without spec to avoid async issues
    executor = MagicMock()

    async def mock_execute(entity_type, action_name, context):
        entity_id = context.entity.get("id", "unknown")

        # Simulate some actions failing based on entity state
        if "fail" in entity_id:
            return ActionResult(success=False, error="模拟的失败")

        # Simulate precondition failures
        if entity_id == "PO_003":
            return ActionResult(success=False, error="订单必须是草稿状态")

        return ActionResult(success=True, changes={"status": "submitted"})

    executor.execute = mock_execute  # Use real async function, not AsyncMock
    return executor


class TestE2EScenarios:
    """End-to-end scenario tests."""

    @pytest.mark.asyncio
    async def test_scenario_query_purchase_orders(
        self,
        llm_config,
        neo4j_config
    ):
        """Scenario: User queries for purchase orders.

        User: "查找所有订单"
        Expected: Agent uses query tools to find orders
        """
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
        )

        events = []
        async for event in agent.astream_chat("查找所有订单"):
            events.append(event)
            if event.get("type") == "done":
                break

        # Verify intent was classified as QUERY
        thinking_events = [e for e in events if e.get("type") == "thinking"]
        assert len(thinking_events) > 0

        # Verify we got a done event
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_scenario_list_available_actions(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: User wants to know what actions are available.

        User: "PurchaseOrder 有哪些操作"
        Expected: Agent lists available actions
        """
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_registry=sample_action_registry,
        )

        actions = await agent.get_available_actions("PurchaseOrder")

        assert len(actions) == 1
        assert actions[0]["entity_type"] == "PurchaseOrder"
        assert actions[0]["action_name"] == "submit"
        assert actions[0]["has_effect"] is True

    @pytest.mark.asyncio
    async def test_scenario_single_action_execution(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: User executes an action on a single entity.

        User: "提交订单 PO_001"
        Expected: Agent validates and executes the action
        """
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=_create_mock_action_executor(),
            action_registry=sample_action_registry,
        )

        # First validate the action can be executed
        with patch('app.services.graph_tools.GraphTools') as mock_graph_tools:
            mock_tools = MagicMock()
            mock_tools.search_instances = AsyncMock(return_value=[
                {"name": "PO_001", "labels": ["PurchaseOrder"], "properties": {"status": "draft"}}
            ])
            mock_graph_tools.return_value = mock_tools

            result = await agent.validate_action(
                entity_type="PurchaseOrder",
                action_name="submit",
                entity_id="PO_001"
            )

            assert result["can_execute"] is True

    @pytest.mark.asyncio
    async def test_scenario_batch_action_with_mixed_results(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: User executes action on multiple entities with mixed results.

        User: "提交所有订单"
        Expected: Some succeed, some fail with reasons
        """
        from app.services.batch_executor import BatchActionExecutor
        from app.services.batch_executor import BatchExecutionConfig

        # Create batch executor
        executor = BatchActionExecutor(
            action_executor=_create_mock_action_executor(),
            get_session_func=lambda: _mock_session_generator(),
            get_entity_data_func=_mock_get_entity_data
        )

        # Prepare executions - mixed success/failure
        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_001", "params": {}},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_fail_001", "params": {}},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_002", "params": {}},
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_003", "params": {}},
        ]

        result = await executor.execute_batch(executions)

        # Verify mixed results
        assert result.total == 4
        assert result.succeeded > 0  # At least some succeeded
        assert result.failed > 0  # At least some failed
        assert len(result.successes) + len(result.failures) == 4

    @pytest.mark.asyncio
    async def test_scenario_action_precondition_failure(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: User tries to execute action but precondition fails.

        User: "提交订单 PO_003" (which is not in draft status)
        Expected: Agent reports precondition failure
        """
        from app.services.batch_executor import BatchActionExecutor

        async def get_pending_data(entity_type, entity_id):
            return {"name": entity_id, "status": "pending"}  # Not draft

        executor = BatchActionExecutor(
            action_executor=_create_mock_action_executor(),
            get_session_func=lambda: _mock_session_generator(),
            get_entity_data_func=get_pending_data
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": "PO_003", "params": {}},
        ]

        result = await executor.execute_batch(executions)

        # Should fail due to precondition
        assert result.total == 1
        assert result.failed == 1
        assert result.succeeded == 0

    @pytest.mark.asyncio
    async def test_scenario_concurrent_execution_performance(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: Verify concurrent execution is faster than serial.

        User: "支付20个发票"
        Expected: Actions execute concurrently (not serially)
        """
        import time
        from app.services.batch_executor import BatchActionExecutor, BatchExecutionConfig

        async def get_unpaid_data(entity_type, entity_id):
            return {"name": entity_id, "status": "unpaid"}

        executor = BatchActionExecutor(
            action_executor=_create_slow_action_executor(delay_seconds=0.05),
            get_session_func=lambda: _mock_session_generator(),
            get_entity_data_func=get_unpaid_data
        )

        # Create 20 executions
        executions = [
            {"entity_type": "Invoice", "action_name": "pay", "entity_id": f"INV_{i:03d}", "params": {}}
            for i in range(20)
        ]

        config = BatchExecutionConfig(max_concurrent=10)

        start = time.time()
        result = await executor.execute_batch(executions, config=config)
        duration = time.time() - start

        assert result.total == 20
        assert result.succeeded == 20

        # With concurrency=10 and 50ms per action, should take ~0.1s (2 batches)
        # Serial would take 20 * 0.05 = 1.0s
        assert duration < 0.5  # Should be much faster than serial

    @pytest.mark.asyncio
    async def test_scenario_progress_tracking_during_batch(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: Verify progress updates during batch execution.

        User: "提交所有订单"
        Expected: Real-time progress updates as each action completes
        """
        from app.services.batch_executor import BatchActionExecutor

        executor = BatchActionExecutor(
            action_executor=_create_mock_action_executor(),
            get_session_func=lambda: _mock_session_generator(),
            get_entity_data_func=_mock_get_entity_data
        )

        executions = [
            {"entity_type": "PurchaseOrder", "action_name": "submit", "entity_id": f"PO_{i:03d}", "params": {}}
            for i in range(5)
        ]

        progress_updates = []

        async def track_progress(update):
            progress_updates.append(update)

        result = await executor.execute_batch(executions, progress_callback=track_progress)

        # Should get progress updates for each execution
        assert len(progress_updates) == 5

        # Each update should have the required fields
        for update in progress_updates:
            assert update["type"] == "action_progress"
            assert "completed" in update
            assert "total" in update
            assert update["total"] == 5
            assert "entity_id" in update

    @pytest.mark.asyncio
    async def test_scenario_empty_action_list(
        self,
        llm_config,
        neo4j_config,
        sample_action_registry
    ):
        """Scenario: User tries to execute on empty entity list.

        Expected: Graceful handling with clear message
        """
        from app.services.batch_executor import BatchActionExecutor

        executor = BatchActionExecutor(
            action_executor=_create_mock_action_executor(),
            get_session_func=lambda: _mock_session_generator(),
        )

        result = await executor.execute_batch([])

        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0


def _mock_session_generator():
    """Create a mock Neo4j session generator."""
    async def gen():
        session = AsyncMock()
        yield session
    return gen()


def _create_mock_action_executor():
    """Create a mock action executor (without spec for better async handling)."""
    from app.rule_engine.action_executor import ActionExecutor

    # Create a simple class that implements the executor interface
    class MockActionExecutor:
        async def execute(self, entity_type, action_name, context):
            entity_id = context.entity.get("id", "unknown")

            # Simulate some actions failing based on entity state
            if "fail" in entity_id:
                return ActionResult(success=False, error="模拟的失败")

            # Simulate precondition failures
            if entity_id == "PO_003":
                return ActionResult(success=False, error="订单必须是草稿状态")

            return ActionResult(success=True, changes={"status": "submitted"})

    return MockActionExecutor()


def _create_slow_action_executor(delay_seconds: float = 0.05):
    """Create a slow action executor for performance testing."""
    from app.rule_engine.action_executor import ActionExecutor

    # Create a simple class that implements the executor interface
    class SlowActionExecutor:
        async def execute(self, entity_type, action_name, context):
            await asyncio.sleep(delay_seconds)
            return ActionResult(success=True, changes={"status": "paid"})

    return SlowActionExecutor()


async def _mock_get_entity_data(entity_type: str, entity_id: str) -> dict:
    """Mock function to get entity data (async version)."""
    return {"name": entity_id, "status": "draft"}
