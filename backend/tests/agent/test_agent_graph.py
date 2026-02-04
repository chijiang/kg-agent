"""Tests for LangGraph construction and nodes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.services.agent.graph import create_agent_graph, route_decision
from app.services.agent.nodes import AgentNodes
from app.services.agent.state import AgentState, UserIntent


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    llm.astream = AsyncMock()
    return llm


@pytest.fixture
def mock_query_tools():
    """Create mock query tools."""
    tool = MagicMock()
    tool.name = "test_tool"
    return [tool]


class TestRouteDecision:
    """Test route_decision function."""

    def test_route_to_query_tools(self):
        """Test routing to query_tools for QUERY intent."""
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "user_intent": UserIntent.QUERY,
        }

        result = route_decision(state)

        assert result == "query_tools"

    def test_route_to_action_tools(self):
        """Test routing to action_tools for ACTION intent."""
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "user_intent": UserIntent.ACTION,
        }

        result = route_decision(state)

        assert result == "action_tools"

    def test_route_to_answer(self):
        """Test routing to answer for DIRECT_ANSWER intent."""
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
            "user_intent": UserIntent.DIRECT_ANSWER,
        }

        result = route_decision(state)

        assert result == "answer"

    def test_route_default_to_query(self):
        """Test default routing to query_tools when intent is missing."""
        state: AgentState = {
            "messages": [HumanMessage(content="test")],
        }

        result = route_decision(state)

        assert result == "query_tools"


class TestAgentNodes:
    """Test AgentNodes class."""

    @pytest.fixture
    def agent_nodes(self, mock_llm, mock_query_tools):
        """Create an AgentNodes instance for testing."""
        return AgentNodes(llm=mock_llm, query_tools=mock_query_tools)

    @pytest.mark.asyncio
    async def test_router_node_with_query_intent(self, agent_nodes):
        """Test router node classifying as QUERY."""
        # Mock the intent classification
        mock_result = MagicMock()
        mock_result.content = "QUERY"
        agent_nodes.llm.ainvoke = AsyncMock(return_value=mock_result)

        state: AgentState = {
            "messages": [HumanMessage(content="Find all orders")],
        }

        result = await agent_nodes.router_node(state)

        assert result["user_intent"] == UserIntent.QUERY
        assert result["current_step"] == "routed"

    @pytest.mark.asyncio
    async def test_router_node_with_action_intent(self, agent_nodes):
        """Test router node classifying as ACTION."""
        mock_result = MagicMock()
        mock_result.content = "ACTION"
        agent_nodes.llm.ainvoke = AsyncMock(return_value=mock_result)

        state: AgentState = {
            "messages": [HumanMessage(content="Pay all invoices")],
        }

        result = await agent_nodes.router_node(state)

        assert result["user_intent"] == UserIntent.ACTION
        assert result["current_step"] == "routed"

    @pytest.mark.asyncio
    async def test_answer_node(self, agent_nodes):
        """Test answer node generates direct response."""
        mock_response = MagicMock()
        mock_response.content = "Hello! How can I help you today?"
        agent_nodes.llm.ainvoke = AsyncMock(return_value=mock_response)

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
        }

        result = await agent_nodes.answer_node(state)

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][-1], AIMessage)
        assert result["current_step"] == "answered"
        # Just check that content is present
        assert result["messages"][-1].content is not None


class TestCreateAgentGraph:
    """Test create_agent_graph function."""

    def test_graph_creation(self, mock_llm, mock_query_tools):
        """Test that a graph can be created."""
        graph = create_agent_graph(llm=mock_llm, query_tools=mock_query_tools)

        assert graph is not None
        # Graph should have nodes
        assert hasattr(graph, "nodes")

    def test_graph_with_memory(self, mock_llm, mock_query_tools):
        """Test graph creation with memory enabled."""
        graph = create_agent_graph(
            llm=mock_llm,
            query_tools=mock_query_tools,
            with_memory=True
        )

        assert graph is not None

    def test_graph_without_memory(self, mock_llm, mock_query_tools):
        """Test graph creation with memory disabled."""
        graph = create_agent_graph(
            llm=mock_llm,
            query_tools=mock_query_tools,
            with_memory=False
        )

        assert graph is not None
