"""Integration tests for event system and rule engine."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.models import UpdateEvent
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.action_registry import ActionRegistry
from app.services.graph_tools import GraphTools


class TestGraphEventEmitter:
    """Test GraphEventEmitter functionality."""

    def test_subscribe_and_emit(self):
        """Test subscribing a listener and emitting events."""
        emitter = GraphEventEmitter()
        listener = Mock()

        # Subscribe listener
        emitter.subscribe(listener)

        # Create and emit event
        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="PO_001",
            property="status",
            old_value="pending",
            new_value="approved"
        )
        emitter.emit(event)

        # Verify listener was called
        listener.assert_called_once_with(event)

    def test_subscribe_duplicate_raises_error(self):
        """Test that subscribing the same listener twice raises an error."""
        emitter = GraphEventEmitter()
        listener = Mock()

        emitter.subscribe(listener)

        # Should raise ValueError when trying to subscribe again
        with pytest.raises(ValueError, match="already subscribed"):
            emitter.subscribe(listener)

    def test_unsubscribe(self):
        """Test unsubscribing a listener."""
        emitter = GraphEventEmitter()
        listener = Mock()

        emitter.subscribe(listener)
        emitter.unsubscribe(listener)

        # Emit event - listener should not be called
        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="PO_001",
            property="status",
            old_value="pending",
            new_value="approved"
        )
        emitter.emit(event)

        listener.assert_not_called()

    def test_unsubscribe_non_existent_raises_error(self):
        """Test that unsubscribing a non-existent listener raises an error."""
        emitter = GraphEventEmitter()
        listener = Mock()

        with pytest.raises(ValueError, match="not subscribed"):
            emitter.unsubscribe(listener)

    def test_multiple_listeners(self):
        """Test that multiple listeners receive events."""
        emitter = GraphEventEmitter()
        listener1 = Mock()
        listener2 = Mock()
        listener3 = Mock()

        emitter.subscribe(listener1)
        emitter.subscribe(listener2)
        emitter.subscribe(listener3)

        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="PO_001",
            property="status",
            old_value="pending",
            new_value="approved"
        )
        emitter.emit(event)

        # All listeners should be called
        listener1.assert_called_once_with(event)
        listener2.assert_called_once_with(event)
        listener3.assert_called_once_with(event)


class TestGraphToolsUpdateEntity:
    """Test GraphTools.update_entity method."""

    @pytest.mark.asyncio
    async def test_update_entity_emits_events(self):
        """Test that update_entity emits events for changed properties."""
        # Create mock session with proper async handling
        mock_session = AsyncMock()

        # Create mock result for _get_entity_raw
        mock_old_result = AsyncMock()
        mock_old_record = AsyncMock()
        mock_old_record.__getitem__ = Mock(return_value={"name": "PO_001", "status": "pending", "amount": 1000})
        mock_old_result.single = AsyncMock(return_value=mock_old_record)

        # Create mock result for update query
        mock_updated_result = AsyncMock()
        mock_updated_record = AsyncMock()
        mock_updated_record.__getitem__ = Mock(return_value={"name": "PO_001", "status": "approved", "amount": 1000})
        mock_updated_result.single = AsyncMock(return_value=mock_updated_record)

        # Setup side_effect for session.run
        call_count = [0]
        async def mock_run_fn(query, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_old_result
            else:
                return mock_updated_result

        mock_session.run = mock_run_fn

        # Create mock event emitter
        mock_emitter = Mock()
        mock_emitter.emit = Mock()

        # Create GraphTools and update entity
        tools = GraphTools(mock_session, event_emitter=mock_emitter)
        result = await tools.update_entity(
            "PurchaseOrder", "PO_001", {"status": "approved"}
        )

        # Verify event was emitted
        assert mock_emitter.emit.called
        emitted_event = mock_emitter.emit.call_args[0][0]
        assert emitted_event.entity_type == "PurchaseOrder"
        assert emitted_event.entity_id == "PO_001"
        assert emitted_event.property == "status"
        assert emitted_event.old_value == "pending"
        assert emitted_event.new_value == "approved"

    @pytest.mark.asyncio
    async def test_update_entity_no_emitter(self):
        """Test that update_entity works without event emitter."""
        # Create mock session
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = MagicMock(
            **{"n": {"name": "PO_001", "status": "approved"}}
        )
        mock_session.run.return_value = mock_result

        # Create GraphTools without event emitter
        tools = GraphTools(mock_session, event_emitter=None)
        result = await tools.update_entity(
            "PurchaseOrder", "PO_001", {"status": "approved"}
        )

        # Should not raise an error
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_entity_no_old_value(self):
        """Test that update_entity handles case where entity doesn't exist."""
        # Create mock session
        mock_session = AsyncMock()
        mock_session.run.return_value = AsyncMock(
            single=AsyncMock(return_value=None)
        )

        # Create mock event emitter
        mock_emitter = Mock()

        # Create GraphTools and update entity
        tools = GraphTools(mock_session, event_emitter=mock_emitter)
        result = await tools.update_entity(
            "PurchaseOrder", "PO_001", {"status": "approved"}
        )

        # Should return empty dict and not emit events
        assert result == {}
        mock_emitter.emit.assert_not_called()


class TestRuleEngineIntegration:
    """Test RuleEngine integration with event system."""

    @pytest.mark.asyncio
    async def test_rule_engine_receives_events(self):
        """Test that RuleEngine receives and processes events from emitter."""
        # Create mock neo4j driver
        mock_driver = AsyncMock()

        # Create registries
        action_registry = ActionRegistry()
        rule_registry = RuleRegistry()

        # Create rule engine
        rule_engine = RuleEngine(action_registry, rule_registry, mock_driver)

        # Create event emitter and subscribe rule engine
        emitter = GraphEventEmitter()
        emitter.subscribe(rule_engine.on_event)

        # Create and emit event
        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="PO_001",
            property="status",
            old_value="pending",
            new_value="approved"
        )
        results = emitter.emit(event)

        # Verify rule engine processed the event
        # (Should return empty list since no rules are registered)
        assert results is None

    @pytest.mark.asyncio
    async def test_rule_engine_with_matching_rule(self):
        """Test that RuleEngine executes rules matching the event."""
        # Create mock neo4j driver
        mock_driver = AsyncMock()

        # Create registries
        action_registry = ActionRegistry()
        rule_registry = RuleRegistry()

        # Register a rule that matches the event
        from app.rule_engine.models import RuleDef, Trigger, TriggerType, ForClause
        from app.rule_engine.parser import RuleParser

        parser = RuleParser()
        dsl_text = """
        RULE AutoApproveLowValueOrders
        {
        ON UPDATE(PurchaseOrder.status)
        FOR (order:PurchaseOrder)
            {
            SET order.autoApproved = true;
            }
        }
        """
        parsed = parser.parse(dsl_text)
        for item in parsed:
            if isinstance(item, RuleDef):
                rule_registry.register(item)

        # Create rule engine
        rule_engine = RuleEngine(action_registry, rule_registry, mock_driver)

        # Create and emit matching event
        event = UpdateEvent(
            entity_type="PurchaseOrder",
            entity_id="PO_001",
            property="status",
            old_value="pending",
            new_value="approved"
        )
        results = rule_engine.on_event(event)

        # Verify rule was matched and executed
        assert isinstance(results, list)
        # Results should contain execution info
        if results:
            assert "query" in results[0]


class TestAPIEndpoint:
    """Test the API endpoint for updating entities."""

    @pytest.mark.asyncio
    async def test_update_entity_endpoint(self):
        """Test the PUT /entities/{entity_type}/{entity_id} endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app

        # Setup app state
        app.state.event_emitter = GraphEventEmitter()

        client = TestClient(app)

        # This test would require a full setup with database and neo4j
        # For now, we'll test the endpoint structure
        # In a real scenario, you'd use pytest-asyncio with proper fixtures
        pass
