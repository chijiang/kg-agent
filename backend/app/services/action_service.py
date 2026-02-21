"""Shared action service layer.

Provides common business logic for action operations, used by both
the MCP action server and the agent_tools action tools to ensure
consistency and avoid code duplication.
"""

import logging
from typing import Any

from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.models import ActionDef
from app.services.pg_graph_storage import PGGraphStorage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------


async def load_actions_from_db(registry: ActionRegistry) -> int:
    """Load active ActionDefinition records from the database into a registry.

    Args:
        registry: ActionRegistry to populate

    Returns:
        Number of actions loaded
    """
    from app.core.database import async_session
    from app.models.rule import ActionDefinition
    from app.rule_engine.models import ActionDef
    from app.rule_engine.parser import RuleParser
    from sqlalchemy import select

    count = 0
    parser = RuleParser()

    async with async_session() as session:
        result = await session.execute(
            select(ActionDefinition).where(ActionDefinition.is_active == True)
        )
        db_actions = result.scalars().all()

        for db_action in db_actions:
            try:
                parsed = parser.parse(db_action.dsl_content)
                for item in parsed:
                    if isinstance(item, ActionDef):
                        registry.register(item)
                        count += 1
                logger.info(f"Loaded action '{db_action.name}' from database")
            except Exception as e:
                logger.warning(f"Failed to load action '{db_action.name}': {e}")

    logger.info(f"Loaded {count} actions from database into registry")
    return count


# ---------------------------------------------------------------------------
# Entity data retrieval
# ---------------------------------------------------------------------------


async def get_entity_data(
    session: Any,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any] | None:
    """Retrieve entity data from the database strictly using numeric ID.

    Args:
        session: Active database session
        entity_type: Entity type/label
        entity_id: Entity database identifier (must be numeric)

    Returns:
        Entity properties dict, or None if not found or ID is not numeric
    """
    if not entity_id.isdigit():
        logger.warning(f"get_entity_data: Non-numeric ID provided: {entity_id}")
        return None

    storage = PGGraphStorage(session)
    data = await storage.get_entity_by_id(int(entity_id))

    if data and data.get("entity_type") == entity_type:
        return data.get("properties", {})

    return None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_action_as_dict(action: ActionDef) -> dict[str, Any]:
    """Format an ActionDef as a serializable dict (for MCP / API).

    Args:
        action: ActionDef to format

    Returns:
        Dictionary representation of the action
    """
    return {
        "name": action.action_name,
        "entity_type": action.entity_type,
        "description": action.description,
        "parameters": [
            {"name": p.name, "type": p.param_type, "optional": p.optional}
            for p in (action.parameters or [])
        ],
        "preconditions": [
            {
                "name": p.name or f"Check {i}",
                "rule": _stringify_ast(p.condition),
                "on_failure": p.on_failure,
            }
            for i, p in enumerate(action.preconditions or [], 1)
        ],
        "has_effect": action.effect is not None,
    }


def format_action_as_text(action: ActionDef) -> str:
    """Format an ActionDef as human-readable text (for LLM agent).

    Args:
        action: ActionDef to format

    Returns:
        Formatted string representation
    """
    output = [f"Action: {action.entity_type}.{action.action_name}"]
    if action.description:
        output.append(f"  Description: {action.description}")

    # Parameters
    if action.parameters:
        output.append("  Parameters:")
        for param in action.parameters:
            optional = "optional" if param.optional else "required"
            output.append(f"    - {param.name} ({param.param_type}, {optional})")
    else:
        output.append("  Parameters: None")

    # Preconditions
    if action.preconditions:
        output.append("  Preconditions (All must be true):")
        for i, precond in enumerate(action.preconditions, 1):
            name = precond.name or f"Check {i}"
            rule_str = _stringify_ast(precond.condition)
            output.append(f"    {i}. {name}:")
            output.append(f"       Rule: {rule_str}")
            output.append(f"       Error Message if False: {precond.on_failure}")
    else:
        output.append("  Preconditions: None")

    # Effect
    if action.effect:
        output.append("  Effect: Yes (modifies state)")
    else:
        output.append("  Effect: None (read-only)")

    return "\n".join(output)


def _stringify_ast(ast: Any) -> str:
    """Convert an AST node back into a DSL-like string for display.

    This helps the LLM agent understand the underlying logic of
    preconditions and rules instead of just seeing failure messages.
    """
    if ast is None:
        return "null"
    if isinstance(ast, str):
        return f"'{ast}'"
    if isinstance(ast, (int, float, bool)):
        return str(ast)

    if isinstance(ast, tuple):
        if not ast:
            return ""
        op = ast[0]

        # Comparison: (op, operator, left, right)
        if op == "op" and len(ast) == 4:
            return f"({_stringify_ast(ast[2])} {ast[1]} {_stringify_ast(ast[3])})"

        # Logical: (and/or, left, right)
        if op in ("and", "or") and len(ast) == 3:
            return f"({_stringify_ast(ast[1])} {op.upper()} {_stringify_ast(ast[2])})"

        # Not: (not, operand)
        if op == "not" and len(ast) == 2:
            return f"NOT {_stringify_ast(ast[1])}"

        # Identifier: (id, path)
        if op == "id" and len(ast) == 2:
            return str(ast[1])

        # IS NULL: (is_null, path, is_not)
        if op == "is_null" and len(ast) == 3:
            not_str = " NOT" if ast[2] else ""
            path_str = _stringify_ast(ast[1])
            return f"{path_str} IS{not_str} NULL"

        # Call: (call, name, args)
        if op == "call" and len(ast) >= 2:
            name = ast[1]
            args = ast[2] if len(ast) > 2 and ast[2] is not None else []
            args_str = ", ".join([_stringify_ast(arg) for arg in args])
            return f"{name}({args_str})"

        # Exists: (exists, pattern)
        if op == "exists":
            return "EXISTS(...)"

        # Node pattern (in exists): (node, var, type_name)
        if op == "node" and len(ast) == 3:
            type_suffix = f":{ast[2]}" if ast[2] else ""
            return f"({ast[1]}{type_suffix})"

    if isinstance(ast, list):
        return "[" + ", ".join([_stringify_ast(i) for i in ast]) + "]"

    return str(ast)


# ---------------------------------------------------------------------------
# Action listing / lookup
# ---------------------------------------------------------------------------


def list_actions(
    registry: ActionRegistry,
    entity_type: str,
) -> list[ActionDef]:
    """List actions for an entity type.

    Args:
        registry: ActionRegistry to query
        entity_type: Entity type to filter by

    Returns:
        List of ActionDef objects
    """
    return registry.list_by_entity(entity_type)


def get_action_detail(
    registry: ActionRegistry,
    entity_type: str,
    action_name: str,
) -> ActionDef | None:
    """Look up a single action.

    Args:
        registry: ActionRegistry to query
        entity_type: Entity type
        action_name: Action name

    Returns:
        ActionDef or None
    """
    return registry.lookup(entity_type, action_name)


# ---------------------------------------------------------------------------
# Precondition validation
# ---------------------------------------------------------------------------


async def validate_preconditions(
    registry: ActionRegistry,
    session: Any,
    entity_type: str,
    action_name: str,
    entity_id: str,
) -> dict[str, Any]:
    """Validate action preconditions against an entity.

    Args:
        registry: ActionRegistry to look up the action
        session: Database session for entity data
        entity_type: Entity type
        action_name: Action name
        entity_id: Entity identifier

    Returns:
        Dict with 'valid' bool, optional 'error' or 'errors' list
    """
    action = registry.lookup(entity_type, action_name)
    if not action:
        return {
            "valid": False,
            "error": f"Action {entity_type}.{action_name} not found",
        }

    entity_data = await get_entity_data(session, entity_type, entity_id)
    if not entity_data:
        return {"valid": False, "error": f"Entity {entity_type} {entity_id} not found"}

    context = EvaluationContext(
        entity={**entity_data, "id": entity_id},
        old_values={},
        session=session,
    )
    evaluator = ExpressionEvaluator(context)

    failures = []
    for precondition in action.preconditions or []:
        try:
            result = await evaluator.evaluate(precondition.condition)
            if not result:
                failures.append(precondition.on_failure)
        except Exception as e:
            failures.append(f"Error evaluating: {e}")

    if failures:
        return {"valid": False, "errors": failures}
    return {"valid": True}


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------


async def execute_single_action(
    executor: ActionExecutor,
    session: Any,
    entity_type: str,
    action_name: str,
    entity_id: str,
    params: dict[str, Any] | None = None,
    actor_name: str | None = None,
    actor_type: str | None = None,
) -> dict[str, Any]:
    """Execute a single action on an entity.

    Args:
        executor: ActionExecutor instance
        session: Active database session (will be committed on success)
        entity_type: Entity type
        action_name: Action name
        entity_id: Entity identifier
        params: Optional action parameters
        actor_name: Optional actor name
        actor_type: Optional actor type

    Returns:
        Dict with 'success', 'error', 'changes' keys
    """
    entity_data = await get_entity_data(session, entity_type, entity_id)
    if not entity_data:
        return {
            "success": False,
            "error": f"Entity {entity_type} {entity_id} not found",
        }

    context = EvaluationContext(
        entity={**entity_data, "id": entity_id},
        old_values={},
        variables=params or {},
        session=session,
    )

    try:
        result = await executor.execute(
            entity_type,
            action_name,
            context,
            actor_name=actor_name,
            actor_type=actor_type,
        )
        if result.success:
            await session.commit()

        return {
            "success": result.success,
            "error": result.error,
            "changes": result.changes,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
