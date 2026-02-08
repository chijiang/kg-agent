from contextlib import asynccontextmanager
from typing import Any, List
from pathlib import Path
import logging

from fastmcp import FastMCP

from app.core.database import async_session
from app.services.pg_graph_storage import PGGraphStorage
from app.services.agent_tools.action_tools import (
    ActionRegistry,
    ActionExecutor,
)
from app.rule_engine.models import ActionDef

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Action Server")

# Initialize services
action_registry = ActionRegistry()
rules_dir = Path("backend/rules")
if rules_dir.exists():
    for dsl_file in rules_dir.glob("*.dsl"):
        try:
            action_registry.load_from_file(str(dsl_file))
            logger.info(f"Loaded rules from {dsl_file}")
        except Exception as e:
            logger.error(f"Failed to load rules from {dsl_file}: {e}")
else:
    logger.warning(f"Rules directory {rules_dir} not found")


async def get_executor() -> ActionExecutor:
    # We pass None for event_emitter for now as we don't have a global one here
    return ActionExecutor(registry=action_registry)


async def _get_entity_data(
    session, entity_type: str, entity_id: str
) -> dict[str, Any] | None:
    storage = PGGraphStorage(session)
    entity = await storage.get_entity_by_name(entity_id, entity_type)
    if entity:
        return entity.get("properties", {})
    return None


# Helper to format action def to dict for serialization
def _format_action(action: ActionDef) -> dict[str, Any]:
    return {
        "name": action.action_name,
        "description": action.description,
        "parameters": [
            {"name": p.name, "type": p.param_type, "optional": p.optional}
            for p in action.parameters
        ],
        "preconditions": (
            [
                {"condition": p.condition, "on_failure": p.on_failure}
                for p in action.preconditions
            ]
            if action.preconditions
            else []
        ),
    }


@mcp.tool()
async def list_available_actions(entity_type: str) -> list[dict[str, Any]]:
    """List available actions for a given entity type.

    Args:
        entity_type: The type of entity (e.g., PurchaseOrder, Supplier)
    """
    actions = action_registry.list_by_entity(entity_type)
    return [_format_action(a) for a in actions]


@mcp.tool()
async def get_action_details(
    entity_type: str, action_name: str
) -> dict[str, Any] | None:
    """Get details for a specific action.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
    """
    action = action_registry.lookup(entity_type, action_name)
    if action:
        return _format_action(action)
    return None


@mcp.tool()
async def validate_action_preconditions(
    entity_type: str, action_name: str, entity_id: str
) -> dict[str, Any]:
    """Validate if an action can be executed on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
    """
    executor = await get_executor()

    async with async_session() as session:
        # Get entity data
        entity_data = await _get_entity_data(session, entity_type, entity_id)
        if not entity_data:
            return {
                "valid": False,
                "error": f"Entity {entity_type} {entity_id} not found",
            }

        # Create context
        from app.rule_engine.context import EvaluationContext

        context = EvaluationContext(
            entity={"id": entity_id, **entity_data}, session=session
        )

        action = action_registry.lookup(entity_type, action_name)
        if not action:
            return {"valid": False, "error": f"Action not found"}

        from app.rule_engine.evaluator import ExpressionEvaluator

        evaluator = ExpressionEvaluator(context)

        failures = []
        for precondition in action.preconditions:
            result = await evaluator.evaluate(precondition.condition)
            if not result:
                failures.append(precondition.on_failure)

        if failures:
            return {"valid": False, "errors": failures}

        return {"valid": True}


@mcp.tool()
async def execute_action(
    entity_type: str,
    action_name: str,
    entity_id: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action on an entity.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_id: The ID of the entity instance
        params: Optional parameters for the action
    """
    executor = await get_executor()

    async with async_session() as session:
        # Get entity data
        entity_data = await _get_entity_data(session, entity_type, entity_id)
        if not entity_data:
            return {
                "success": False,
                "error": f"Entity {entity_type} {entity_id} not found",
            }

        # Create context
        from app.rule_engine.context import EvaluationContext

        context = EvaluationContext(
            entity={"id": entity_id, **entity_data},
            variables=params or {},
            session=session,
        )

        try:
            result = await executor.execute(entity_type, action_name, context)
            await session.commit()
            return {
                "success": result.success,
                "error": result.error,
                "changes": result.changes,
            }
        except Exception as e:
            await session.rollback()
            return {"success": False, "error": str(e)}


@mcp.tool()
async def batch_execute_action(
    entity_type: str,
    action_name: str,
    entity_ids: List[str],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action on multiple entities.

    Args:
        entity_type: The type of entity
        action_name: The name of the action
        entity_ids: List of entity IDs
        params: Optional parameters for the action
    """
    executor = await get_executor()
    results = []

    async with async_session() as session:
        for eid in entity_ids:
            try:
                # Get entity data
                entity_data = await _get_entity_data(session, entity_type, eid)
                if not entity_data:
                    results.append(
                        {"id": eid, "success": False, "error": "Entity not found"}
                    )
                    continue

                # Create context
                from app.rule_engine.context import EvaluationContext

                context = EvaluationContext(
                    entity={"id": eid, **entity_data},
                    variables=params or {},
                    session=session,
                )

                res = await executor.execute(entity_type, action_name, context)
                results.append(
                    {
                        "id": eid,
                        "success": res.success,
                        "error": res.error,
                        "changes": res.changes,
                    }
                )
            except Exception as e:
                results.append({"id": eid, "success": False, "error": str(e)})

        await session.commit()

    return {"summary": "Batch execution completed", "results": results}
