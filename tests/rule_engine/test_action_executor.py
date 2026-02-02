"""Tests for ActionExecutor."""

import pytest
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import ActionDef, Parameter, Precondition, SetStatement
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator


def test_execution_result_success():
    """Test ExecutionResult for successful execution."""
    result = ExecutionResult(
        success=True,
        error=None,
        changes={"status": "Submitted"}
    )

    assert result.success is True
    assert result.error is None
    assert result.changes == {"status": "Submitted"}


def test_execution_result_failure():
    """Test ExecutionResult for failed execution."""
    result = ExecutionResult(
        success=False,
        error="Precondition failed",
        changes={}
    )

    assert result.success is False
    assert result.error == "Precondition failed"
    assert result.changes == {}


def test_execute_with_passing_preconditions():
    """Test executing an action where all preconditions pass."""
    registry = ActionRegistry()

    # Register an action with preconditions that will pass
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
            ),
            Precondition(
                name="amountCheck",
                condition=("op", ">", "this.amount", 0),
                on_failure="Amount must be positive"
            )
        ],
        effect=None
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    # Create entity data that satisfies all preconditions
    entity = {
        "status": "Draft",
        "amount": 100
    }

    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "submit", context)

    assert result.success is True
    assert result.error is None


def test_execute_with_failing_precondition():
    """Test executing an action where a precondition fails."""
    registry = ActionRegistry()

    # Register an action with a precondition that will fail
    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
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

    executor = ActionExecutor(registry)

    # Create entity data that does NOT satisfy the precondition
    entity = {
        "status": "Submitted",
        "amount": 100
    }

    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "submit", context)

    assert result.success is False
    assert result.error == "Only draft orders can be submitted"


def test_execute_with_effect():
    """Test executing an action with an effect block."""
    from app.rule_engine.parser import EffectBlock

    registry = ActionRegistry()

    # Register an action with an effect
    effect = EffectBlock(statements=[
        SetStatement(target="this.status", value="Submitted"),
        SetStatement(target="this.submittedAt", value=("call", "NOW", []))
    ])

    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name=None,
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Must be draft"
            )
        ],
        effect=effect
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    entity = {
        "status": "Draft",
        "amount": 100
    }

    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "submit", context)

    assert result.success is True
    # The changes should contain the status update
    # Note: submittedAt would be a function call result
    assert "status" in result.changes or len(result.changes) > 0


def test_execute_nonexistent_action():
    """Test executing a non-existent action."""
    registry = ActionRegistry()
    executor = ActionExecutor(registry)

    entity = {"status": "Draft"}
    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "nonexistent", context)

    assert result.success is False
    assert "not found" in result.error.lower()


def test_execute_with_multiple_preconditions_first_fails():
    """Test that execution stops at the first failing precondition."""
    registry = ActionRegistry()

    # Register an action with multiple preconditions where the first fails
    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Status check failed"
            ),
            Precondition(
                name="amountCheck",
                condition=("op", ">", "this.amount", 0),
                on_failure="Amount check failed"
            )
        ],
        effect=None
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    # Entity fails the first precondition but would pass the second
    entity = {
        "status": "Submitted",  # Fails first precondition
        "amount": 100  # Would pass second precondition
    }

    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "submit", context)

    assert result.success is False
    # Should report the first failure
    assert result.error == "Status check failed"


def test_execute_with_no_preconditions():
    """Test executing an action with no preconditions."""
    registry = ActionRegistry()

    # Register an action with no preconditions
    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="calculate",
        parameters=[],
        preconditions=[],
        effect=None
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    entity = {"amount": 100}
    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "calculate", context)

    assert result.success is True
    assert result.error is None


def test_execute_with_named_precondition():
    """Test that named preconditions are properly handled."""
    registry = ActionRegistry()

    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name="mustBeDraft",
                condition=("op", "==", "this.status", "Draft"),
                on_failure="Order must be in Draft status"
            )
        ],
        effect=None
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    entity = {"status": "Open"}
    context = EvaluationContext(
        entity=entity,
        old_values={},
        session=None
    )

    result = executor.execute("PurchaseOrder", "submit", context)

    assert result.success is False
    assert result.error == "Order must be in Draft status"


def test_execute_with_complex_precondition():
    """Test executing an action with a complex precondition (AND/OR)."""
    registry = ActionRegistry()

    # Action with complex precondition: status is Draft AND amount > 0
    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name="validation",
                condition=("and", ("op", "==", "this.status", "Draft"), ("op", ">", "this.amount", 0)),
                on_failure="Order must be draft with positive amount"
            )
        ],
        effect=None
    )
    registry.register(action)

    executor = ActionExecutor(registry)

    # Test case 1: Both conditions pass
    entity1 = {"status": "Draft", "amount": 100}
    context1 = EvaluationContext(entity=entity1, old_values={}, session=None)
    result1 = executor.execute("PurchaseOrder", "submit", context1)
    assert result1.success is True

    # Test case 2: First condition fails
    entity2 = {"status": "Submitted", "amount": 100}
    context2 = EvaluationContext(entity=entity2, old_values={}, session=None)
    result2 = executor.execute("PurchaseOrder", "submit", context2)
    assert result2.success is False

    # Test case 3: Second condition fails
    entity3 = {"status": "Draft", "amount": -10}
    context3 = EvaluationContext(entity=entity3, old_values={}, session=None)
    result3 = executor.execute("PurchaseOrder", "submit", context3)
    assert result3.success is False
