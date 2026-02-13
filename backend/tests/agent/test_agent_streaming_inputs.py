"""Tests for streaming tool inputs in EnhancedAgentService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent import EnhancedAgentService


@pytest.fixture
def llm_config():
    return {
        "api_key": "test-key",
        "base_url": "https://api.test.com",
        "model": "gpt-4",
    }


@pytest.mark.asyncio
async def test_astream_chat_includes_tool_inputs(llm_config):
    # Mocking ActionRegistry and ActionToolRegistry to avoid dependencies
    with patch("app.services.agent.agent_service.QueryToolRegistry"), patch(
        "app.services.agent.agent_service.create_agent_graph"
    ) as mock_create_graph:

        # Setup mock graph
        mock_graph = MagicMock()
        mock_create_graph.return_value = mock_graph

        # Mock astream_events to yield a tool start event
        async def mock_astream_events(*args, **kwargs):
            yield {
                "event": "on_tool_start",
                "name": "search_instances",
                "data": {"input": {"query": "test query", "limit": 5}},
            }
            yield {
                "event": "on_chat_model_end",
                "data": {"output": MagicMock(tool_calls=[], content="Final answer")},
            }

        mock_graph.astream_events = mock_astream_events

        agent = EnhancedAgentService(llm_config=llm_config, neo4j_config=None)

        events = []
        async for event in agent.astream_chat("test query"):
            events.append(event)
            if event.get("type") == "done":
                break

        # Verify events
        thinking_events = [e for e in events if e.get("type") == "thinking"]

        # Look for the calling tool event
        tool_event = next(
            (e for e in thinking_events if "Calling tool" in e["content"]), None
        )
        assert tool_event is not None
        assert "`search_instances`" in tool_event["content"]
        assert "```json" in tool_event["content"]
        assert '"query": "test query"' in tool_event["content"]
        assert '"limit": 5' in tool_event["content"]
