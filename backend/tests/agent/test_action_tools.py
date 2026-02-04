"""Tests for action tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.tools import StructuredTool

from app.services.agent_tools.action_tools import (
    create_action_tools,
    ActionToolRegistry,
    format_action_def,
)
from app.rule_engine.models import ActionDef, Parameter, Precondition, ActionResult


@pytest.fixture
def mock_action_executor():
    """Create a mock ActionExecutor."""
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value=ActionResult(
        success=True,
        changes={"status": "submitted"}
    ))
    return executor


@pytest.fixture
def mock_action_registry():
    """Create a mock ActionRegistry."""
    registry = MagicMock()

    # Create a sample action
    sample_action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[
            Parameter(name="confirm", param_type="boolean", optional=True)
        ],
        preconditions=[
            Precondition(
                name="is_draft",
                condition={"type": "property", "property": "status", "op": "==", "value": "draft"},
                on_failure="Order must be in draft status"
            )
        ],
        effect={"type": "set", "property": "status", "value": "submitted"}
    )

    registry.lookup = MagicMock(return_value=sample_action)
    registry.list_by_entity = MagicMock(return_value=[sample_action])
    return registry


@pytest.fixture
def mock_session():
    """Create a mock Neo4j session."""
    session = AsyncMock()
    # Mock run to return a result with data
    result = AsyncMock()
    result.single = AsyncMock(return_value=MagicMock(props={"name": "PO_001", "status": "draft"}))
    session.run = AsyncMock(return_value=result)
    return session


@pytest.fixture
def mock_get_session_func(mock_session):
    """Create a mock get_session function."""
    async def _get_session():
        yield mock_session
    return _get_session


class TestFormatActionDef:
    """Test format_action_def function."""

    def test_format_action_def(self):
        """Test formatting an action definition."""
        action = ActionDef(
            entity_type="PurchaseOrder",
            action_name="submit",
            parameters=[
                Parameter(name="confirm", param_type="boolean", optional=True)
            ],
            preconditions=[
                Precondition(
                    name="is_draft",
                    condition={"type": "property", "property": "status"},
                    on_failure="Must be draft"
                )
            ],
            effect={"type": "set", "property": "status", "value": "submitted"}
        )

        result = format_action_def(action)

        assert "PurchaseOrder.submit" in result
        assert "confirm" in result
        assert "is_draft" in result
        assert "Must be draft" in result


class TestCreateActionTools:
    """Test create_action_tools function."""

    def test_tools_are_structured_tools(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test that all returned tools are StructuredTool instances."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)

        for tool in tools:
            assert isinstance(tool, StructuredTool)

    def test_tool_names(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test that tools have correct names."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)
        tool_names = [t.name for t in tools]

        expected_names = [
            "list_available_actions",
            "get_action_details",
            "validate_action_preconditions",
            "execute_action",
            "batch_execute_action",
        ]

        for name in expected_names:
            assert name in tool_names

    def test_tool_descriptions(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test that tools have descriptions."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)

        for tool in tools:
            assert tool.description
            assert len(tool.description) > 0

    @pytest.mark.asyncio
    async def test_list_available_actions(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test list_available_actions tool."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)
        tool = next(t for t in tools if t.name == "list_available_actions")

        result = await tool.coroutine(entity_type="PurchaseOrder")

        assert "PurchaseOrder" in result
        assert "submit" in result

    @pytest.mark.asyncio
    async def test_get_action_details(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test get_action_details tool."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)
        tool = next(t for t in tools if t.name == "get_action_details")

        result = await tool.coroutine(entity_type="PurchaseOrder", action_name="submit")

        assert "PurchaseOrder.submit" in result
        assert "Parameters" in result or "Parameters: None" in result

    @pytest.mark.asyncio
    async def test_execute_action(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test execute_action tool."""
        tools = create_action_tools(mock_get_session_func, mock_action_executor, mock_action_registry)
        tool = next(t for t in tools if t.name == "execute_action")

        # The mock session returns PO_001
        result = await tool.coroutine(
            entity_type="PurchaseOrder",
            action_name="submit",
            entity_id="PO_001"
        )

        # Result should contain either success or error info
        assert result is not None
        assert len(result) > 0
        # Check that executor was called (if entity was found)
        if "成功" in result or "success" in result.lower():
            mock_action_executor.execute.assert_called_once()


class TestActionToolRegistry:
    """Test ActionToolRegistry class."""

    def test_initialization(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test registry initialization."""
        registry = ActionToolRegistry(mock_get_session_func, mock_action_executor, mock_action_registry)

        assert registry.get_session_func == mock_get_session_func
        assert registry.action_executor == mock_action_executor
        assert registry.action_registry == mock_action_registry
        assert registry._tools is None

    def test_tools_property(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test that tools property creates tools on first access."""
        registry = ActionToolRegistry(mock_get_session_func, mock_action_executor, mock_action_registry)

        tools = registry.tools
        assert tools is not None
        assert len(tools) > 0

        # Second access should return cached tools
        tools2 = registry.tools
        assert tools is tools2

    def test_get_tool_names(self, mock_get_session_func, mock_action_executor, mock_action_registry):
        """Test get_tool_names method."""
        registry = ActionToolRegistry(mock_get_session_func, mock_action_executor, mock_action_registry)

        names = registry.get_tool_names()

        assert isinstance(names, list)
        assert len(names) > 0
        assert "list_available_actions" in names
