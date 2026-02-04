"""Integration tests for the enhanced agent system.

These tests verify that all components work together properly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.services.agent import EnhancedAgentService
from app.services.agent.state import AgentState, UserIntent
from app.rule_engine.models import ActionDef, Parameter, ActionResult
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
def mock_action_registry():
    """Create a mock action registry with sample actions."""
    registry = ActionRegistry()

    # Register a sample action
    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[Parameter(name="confirm", param_type="boolean", optional=True)],
        preconditions=[],
        effect={"type": "set", "property": "status", "value": "submitted"}
    )
    registry.register(action)

    return registry


@pytest.fixture
def mock_action_executor():
    """Create a mock action executor."""
    executor = MagicMock(spec=ActionExecutor)

    async def mock_execute(entity_type, action_name, context):
        return ActionResult(success=True, changes={"status": "submitted"})

    executor.execute = AsyncMock(side_effect=mock_execute)
    return executor


class TestEnhancedAgentServiceIntegration:
    """Integration tests for EnhancedAgentService."""

    @pytest.mark.asyncio
    async def test_agent_initialization(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test agent initializes correctly with all dependencies."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        assert agent.llm_config == llm_config
        assert agent.neo4j_config == neo4j_config
        assert agent.action_executor == mock_action_executor
        assert agent.action_registry == mock_action_registry

    @pytest.mark.asyncio
    async def test_agent_stream_thinking_events(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test that agent streams thinking events."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        events = []
        async for event in agent.astream_chat("hello"):
            events.append(event)
            if event.get("type") == "done":
                break

        # Should have at least thinking and done events
        event_types = [e.get("type") for e in events]
        assert "thinking" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_get_available_actions(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test getting available actions for an entity type."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        actions = await agent.get_available_actions("PurchaseOrder")

        assert len(actions) == 1
        assert actions[0]["entity_type"] == "PurchaseOrder"
        assert actions[0]["action_name"] == "submit"

    @pytest.mark.asyncio
    async def test_validate_action(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test action validation."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        # Mock the GraphTools to avoid Neo4j connection
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
            assert "action" in result

    @pytest.mark.asyncio
    async def test_agent_without_action_components(
        self,
        llm_config,
        neo4j_config
    ):
        """Test agent works without action components (query-only mode)."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
        )

        # Should not crash when action components are missing
        actions = await agent.get_available_actions("PurchaseOrder")
        assert actions == []

        result = await agent.validate_action("PurchaseOrder", "submit", "PO_001")
        assert result["can_execute"] is False


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_query_workflow(
        self,
        llm_config,
        neo4j_config
    ):
        """Test a complete query workflow."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
        )

        # Simulate a query
        events = []
        async for event in agent.astream_chat("查找所有订单"):
            events.append(event)
            if event.get("type") == "done":
                break

        # Verify event flow
        event_types = [e.get("type") for e in events]

        # Should have thinking event
        assert "thinking" in event_types

        # Should complete
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_action_workflow_with_mock_tools(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test a complete action workflow with mocked tools."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        # The graph should have both query and action tools
        graph = agent._get_graph()
        assert graph is not None


class TestToolIntegration:
    """Test that tools are properly integrated."""

    @pytest.mark.asyncio
    async def test_query_tools_registered(self, llm_config, neo4j_config):
        """Test that query tools are registered."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
        )

        graph = agent._get_graph()
        assert graph is not None

        # The graph should be constructed without errors
        nodes = graph.nodes
        assert "router" in nodes
        assert "query_tools" in nodes
        assert "answer" in nodes

    @pytest.mark.asyncio
    async def test_action_tools_registered(
        self,
        llm_config,
        neo4j_config,
        mock_action_executor,
        mock_action_registry
    ):
        """Test that action tools are registered when available."""
        agent = EnhancedAgentService(
            llm_config=llm_config,
            neo4j_config=neo4j_config,
            action_executor=mock_action_executor,
            action_registry=mock_action_registry,
        )

        # Force graph creation with action tools
        graph = agent._get_graph()
        assert graph is not None

        # The graph should be constructed with action tools
        nodes = graph.nodes
        assert "router" in nodes
        assert "action_tools" in nodes
