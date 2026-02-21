"""Shared persistence logic for rule engine updates."""

import json
import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PersistenceService:
    """Service for executing property updates on graph entities."""

    @staticmethod
    async def update_property(
        session: AsyncSession,
        entity_type: str,
        entity_id: Any,
        prop_name: str,
        value: Any,
    ) -> bool:
        """Update a single property using jsonb_set to avoid race conditions.

        Args:
            session: Active database session
            entity_type: Entity type
            entity_id: Entity ID (internal UUID or its string representation)
            prop_name: Property name to update
            value: New property value

        Returns:
            True if successful
        """
        try:
            # Ensure entity_id is numeric to match graph_entities integer id column.
            if isinstance(entity_id, str) and entity_id.isdigit():
                numeric_id = int(entity_id)
            elif isinstance(entity_id, int):
                numeric_id = entity_id
            else:
                logger.warning(
                    f"PersistenceService: entity_id {entity_id} is not numeric."
                )
                return False

            # Use jsonb_set(target, path, new_value)
            # path is an array of text
            update_query = text(
                """
                UPDATE graph_entities
                SET properties = jsonb_set(
                    COALESCE(properties, '{}'::jsonb),
                    ARRAY[:prop_name]::text[],
                    CAST(:json_value AS jsonb)
                )
                WHERE id = :numeric_id
                AND entity_type = :entity_type
                """
            )

            json_value = json.dumps(value)

            await session.execute(
                update_query,
                {
                    "numeric_id": numeric_id,
                    "entity_type": entity_type,
                    "prop_name": prop_name,
                    "json_value": json_value,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Error updating property {prop_name} on {entity_id}: {e}")
            return False

    @staticmethod
    async def update_properties(
        session: AsyncSession, entity_type: str, entity_id: Any, changes: dict[str, Any]
    ) -> bool:
        """Update multiple properties.

        Currently implemented as multiple jsonb_set calls for simplicity,
        but could be optimized into a single jsonb_deep_merge if available.

        Args:
            session: Active database session
            entity_type: Entity type
            entity_id: Entity ID
            changes: Dict of property changes

        Returns:
            True if all updates succeeded
        """
        success = True
        for prop_name, value in changes.items():
            res = await PersistenceService.update_property(
                session, entity_type, entity_id, prop_name, value
            )
            if not res:
                success = False
        return success
