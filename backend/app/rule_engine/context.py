"""Evaluation context for expressions."""

from dataclasses import dataclass, field
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession as SQLAsyncSession


@dataclass
class EvaluationContext:
    """Context for evaluating expressions against entity data."""

    entity: dict[str, Any]
    old_values: dict[str, Any]
    session: Optional[SQLAsyncSession] = None  # PostgreSQL DB session
    variables: dict[str, Any] = field(default_factory=dict)

    @property
    def db(self) -> Optional[SQLAsyncSession]:
        """Alias for session for PostgreSQL compatibility."""
        return self.session

    def get_variable(self, name: str) -> Any:
        """Get a variable by name.

        Special variables:
        - "this" returns the current entity

        Args:
            name: Variable name

        Returns:
            Variable value or None if not found
        """
        if name == "this":
            return self.entity
        return self.variables.get(name)

    def resolve_path(self, path: str) -> Any:
        """Resolve a property path to a value.

        Paths can be:
        - "this.prop" -> entity["prop"] or entity["properties"]["prop"]
        - "e.prop" -> variables["e"]["prop"] (if 'e' is in variables)
        - "varName.prop" -> variables["varName"]["prop"]

        Args:
            path: Dot-separated property path

        Returns:
            Resolved value or None if path is invalid
        """
        parts = path.split(".")
        if not parts:
            return None

        # Get the root object
        root_name = parts[0]
        if root_name == "this":
            obj = self.entity
        elif root_name in self.variables:
            obj = self.variables[root_name]
        else:
            # Fallback: maybe it's a direct reference to a variable without a path
            if len(parts) == 1:
                return self.variables.get(root_name)
            return None

        # Navigate through nested properties
        for i, part in enumerate(parts[1:]):
            if isinstance(obj, dict):
                # Try direct access first
                if part in obj:
                    obj = obj[part]
                elif root_name in ("this", "e") and i == 0 and "properties" in obj:
                    # If not found and it's a main entity, check 'properties'
                    props = obj["properties"]
                    if isinstance(props, dict) and part in props:
                        obj = props[part]
                    else:
                        return None
                else:
                    return None
            else:
                return None

        return obj
