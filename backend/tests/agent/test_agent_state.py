"""Tests for agent state definitions."""

import pytest
from app.services.agent.state import (
    AgentState,
    ActionPlan,
    ActionResultSummary,
    StreamEvent,
    UserIntent,
    VALID_INTENTS,
)


class TestUserIntent:
    """Test UserIntent constants."""

    def test_intent_constants(self):
        """Test that intent constants are properly defined."""
        assert UserIntent.QUERY == "query"
        assert UserIntent.ACTION == "action"
        assert UserIntent.DIRECT_ANSWER == "direct_answer"

    def test_valid_intents_set(self):
        """Test that VALID_INTENTS includes all intent constants."""
        assert UserIntent.QUERY in VALID_INTENTS
        assert UserIntent.ACTION in VALID_INTENTS
        assert UserIntent.DIRECT_ANSWER in VALID_INTENTS


class TestActionPlan:
    """Test ActionPlan TypedDict."""

    def test_action_plan_structure(self):
        """Test that ActionPlan can be constructed properly."""
        plan: ActionPlan = {
            "entity_type": "PurchaseOrder",
            "action_name": "submit",
            "target_count": 3,
            "targets": [
                {"entity_id": "PO_001", "entity_name": "Order 1"},
                {"entity_id": "PO_002", "entity_name": "Order 2"},
                {"entity_id": "PO_003", "entity_name": "Order 3"},
            ],
        }

        assert plan["entity_type"] == "PurchaseOrder"
        assert plan["action_name"] == "submit"
        assert plan["target_count"] == 3
        assert len(plan["targets"]) == 3


class TestActionResultSummary:
    """Test ActionResultSummary TypedDict."""

    def test_action_result_summary_structure(self):
        """Test that ActionResultSummary can be constructed properly."""
        summary: ActionResultSummary = {
            "total": 10,
            "succeeded": 8,
            "failed": 2,
            "successes": [
                {"entity_id": "PO_001", "changes": {"status": "submitted"}},
                {"entity_id": "PO_002", "changes": {"status": "submitted"}},
            ],
            "failures": [
                {"entity_id": "PO_003", "error": "Precondition failed"},
                {"entity_id": "PO_004", "error": "Not found"},
            ],
        }

        assert summary["total"] == 10
        assert summary["succeeded"] == 8
        assert summary["failed"] == 2
        assert len(summary["successes"]) == 2
        assert len(summary["failures"]) == 2


class TestStreamEvent:
    """Test StreamEvent TypedDict."""

    def test_thinking_event(self):
        """Test thinking event structure."""
        event: StreamEvent = {
            "type": "thinking",
            "content": "Analyzing request...",
        }

        assert event["type"] == "thinking"
        assert event["content"] == "Analyzing request..."

    def test_content_event(self):
        """Test content event structure."""
        event: StreamEvent = {
            "type": "content",
            "content": "Here is the answer",
        }

        assert event["type"] == "content"
        assert event["content"] == "Here is the answer"

    def test_graph_data_event(self):
        """Test graph_data event structure."""
        event: StreamEvent = {
            "type": "graph_data",
            "nodes": [{"id": "1", "label": "Node 1"}],
            "edges": [{"source": "1", "target": "2"}],
        }

        assert event["type"] == "graph_data"
        assert len(event["nodes"]) == 1
        assert len(event["edges"]) == 1

    def test_action_plan_event(self):
        """Test action_plan event structure."""
        event: StreamEvent = {
            "type": "action_plan",
            "plan": {
                "entity_type": "PurchaseOrder",
                "action_name": "submit",
                "target_count": 1,
                "targets": [{"entity_id": "PO_001", "entity_name": "Order 1"}],
            },
        }

        assert event["type"] == "action_plan"
        assert event["plan"]["action_name"] == "submit"

    def test_action_progress_event(self):
        """Test action_progress event structure."""
        event: StreamEvent = {
            "type": "action_progress",
            "completed": 5,
            "total": 10,
            "entity_id": "PO_001",
            "success": True,
        }

        assert event["type"] == "action_progress"
        assert event["completed"] == 5
        assert event["total"] == 10
        assert event["success"] is True


class TestAgentState:
    """Test AgentState TypedDict."""

    def test_agent_state_minimal(self):
        """Test minimal AgentState construction."""
        from langchain_core.messages import HumanMessage

        state: AgentState = {
            "messages": [HumanMessage(content="Hello")],
        }

        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "Hello"

    def test_agent_state_with_optional_fields(self):
        """Test AgentState with all optional fields."""
        from langchain_core.messages import HumanMessage, AIMessage

        state: AgentState = {
            "messages": [HumanMessage(content="Query"), AIMessage(content="Response")],
            "user_intent": UserIntent.QUERY,
            "current_step": "queried",
            "query_results": [{"tool": "search_instances", "result": "found"}],
            "graph_data": {"nodes": [], "edges": []},
            "action_plan": {
                "entity_type": "Test",
                "action_name": "test",
                "target_count": 0,
                "targets": [],
            },
            "batch_results": {"total": 0, "succeeded": 0, "failed": 0, "successes": [], "failures": []},
        }

        assert state["user_intent"] == UserIntent.QUERY
        assert state["current_step"] == "queried"
        assert len(state["query_results"]) == 1
