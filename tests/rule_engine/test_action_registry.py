"""Tests for ActionRegistry."""

import pytest
from pathlib import Path
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import ActionDef, Parameter, Precondition


def test_register_action():
    """Test registering an action."""
    registry = ActionRegistry()

    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[
            Parameter(name="comment", param_type="string", optional=True)
        ],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Only draft orders can be submitted"
            )
        ],
        effect=None
    )

    registry.register(action)

    # Verify action can be looked up
    retrieved = registry.lookup("PurchaseOrder", "submit")
    assert retrieved is not None
    assert retrieved.entity_type == "PurchaseOrder"
    assert retrieved.action_name == "submit"


def test_lookup_nonexistent():
    """Test looking up a non-existent action."""
    registry = ActionRegistry()

    result = registry.lookup("PurchaseOrder", "nonexistent")
    assert result is None


def test_list_by_entity():
    """Test listing actions for a specific entity type."""
    registry = ActionRegistry()

    # Register multiple actions for different entity types
    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="cancel",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    registry.register(ActionDef(
        entity_type="Supplier",
        action_name="approve",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    # List actions for PurchaseOrder
    po_actions = registry.list_by_entity("PurchaseOrder")
    assert len(po_actions) == 2
    action_names = {a.action_name for a in po_actions}
    assert action_names == {"submit", "cancel"}

    # List actions for Supplier
    supplier_actions = registry.list_by_entity("Supplier")
    assert len(supplier_actions) == 1
    assert supplier_actions[0].action_name == "approve"


def test_list_all():
    """Test listing all registered actions."""
    registry = ActionRegistry()

    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    registry.register(ActionDef(
        entity_type="Supplier",
        action_name="approve",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    all_actions = registry.list_all()
    assert len(all_actions) == 2

    entity_types = {a.entity_type for a in all_actions}
    assert entity_types == {"PurchaseOrder", "Supplier"}


def test_load_from_text():
    """Test loading actions from DSL text."""
    registry = ActionRegistry()

    dsl_text = """
    ACTION PurchaseOrder.submit {
        PRECONDITION statusCheck: this.status == "Draft"
            ON_FAILURE: "Only draft orders can be submitted"
        PRECONDITION: this.amount > 0
            ON_FAILURE: "Amount must be positive"
        EFFECT {
            SET this.status = "Submitted";
        }
    }

    ACTION Supplier.approve {
        PRECONDITION: this.status == "Pending"
            ON_FAILURE: "Only pending suppliers can be approved"
    }
    """

    registry.load_from_text(dsl_text)

    # Verify PurchaseOrder.submit
    po_submit = registry.lookup("PurchaseOrder", "submit")
    assert po_submit is not None
    assert len(po_submit.preconditions) == 2
    assert po_submit.preconditions[0].name == "statusCheck"
    assert po_submit.effect is not None

    # Verify Supplier.approve
    supplier_approve = registry.lookup("Supplier", "approve")
    assert supplier_approve is not None
    assert len(supplier_approve.preconditions) == 1


def test_load_from_file():
    """Test loading actions from a DSL file."""
    registry = ActionRegistry()

    # Create a temporary DSL file
    dsl_file = Path("/tmp/test_actions.dsl")
    dsl_content = """
    ACTION PurchaseOrder.cancel {
        PRECONDITION: this.status == "Open"
            ON_FAILURE: "Cannot cancel"
        EFFECT {
            SET this.status = "Cancelled";
            SET this.cancelledAt = NOW();
        }
    }
    """
    dsl_file.write_text(dsl_content)

    try:
        registry.load_from_file(str(dsl_file))

        action = registry.lookup("PurchaseOrder", "cancel")
        assert action is not None
        assert action.action_name == "cancel"
        assert len(action.effect.statements) == 2
    finally:
        dsl_file.unlink()


def test_load_from_text_with_rules():
    """Test that load_from_text ignores RULE definitions."""
    registry = ActionRegistry()

    dsl_text = """
    ACTION PurchaseOrder.submit {
        PRECONDITION: this.status == "Draft"
            ON_FAILURE: "Only draft orders can be submitted"
    }

    RULE SupplierStatusBlocking PRIORITY 100 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted"]) {
            SET s.locked = true;
        }
    }
    """

    registry.load_from_text(dsl_text)

    # Only the action should be registered
    all_actions = registry.list_all()
    assert len(all_actions) == 1
    assert all_actions[0].action_name == "submit"


def test_register_duplicate_action():
    """Test that registering a duplicate action overwrites the previous one."""
    registry = ActionRegistry()

    # Register first version
    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[
            Parameter(name="comment", param_type="string", optional=True)
        ],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Only draft orders can be submitted"
            )
        ],
        effect=None
    ))

    # Register second version (different preconditions)
    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[
            Parameter(name="comment", param_type="string", optional=True)
        ],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Updated message"
            )
        ],
        effect=None
    ))

    # Verify only one action exists with the updated message
    all_actions = registry.list_all()
    assert len(all_actions) == 1
    assert all_actions[0].preconditions[0].on_failure == "Updated message"


def test_list_by_entity_empty():
    """Test listing actions for an entity with no actions."""
    registry = ActionRegistry()

    actions = registry.list_by_entity("NonExistent")
    assert actions == []


def test_list_all_empty():
    """Test listing all actions when none are registered."""
    registry = ActionRegistry()

    actions = registry.list_all()
    assert actions == []
