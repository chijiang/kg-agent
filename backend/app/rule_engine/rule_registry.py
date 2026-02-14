from typing import Any
from app.rule_engine.base_registry import BaseRegistry
from app.rule_engine.models import RuleDef, Trigger


class RuleRegistry(BaseRegistry):
    """Registry for managing rule definitions.

    The rule registry stores RuleDef objects and provides lookup
    functionality by rule name or trigger type.
    """

    def __init__(self):
        """Initialize an empty registry."""
        super().__init__()
        self._rules: dict[str, RuleDef] = {}
        self._trigger_index: dict[str, list[str]] = {}

    def register(self, rule: RuleDef) -> None:
        """Register a rule definition.

        Args:
            rule: The rule definition to register

        Raises:
            ValueError: If a rule with the same name already exists
        """
        if rule.name in self._rules:
            raise ValueError(f"Rule '{rule.name}' is already registered")

        self._rules[rule.name] = rule

        # Index by trigger for efficient lookup
        trigger_key = self._make_trigger_key(rule.trigger)
        if trigger_key not in self._trigger_index:
            self._trigger_index[trigger_key] = []
        self._trigger_index[trigger_key].append(rule.name)

    def lookup(self, rule_name: str) -> RuleDef | None:
        """Look up a rule by name.

        Args:
            rule_name: The name of the rule to look up

        Returns:
            The rule definition or None if not found
        """
        return self._rules.get(rule_name)

    def get_by_trigger(self, trigger: Trigger) -> list[RuleDef]:
        """Get rules matching a trigger.

        Args:
            trigger: The trigger to match against

        Returns:
            List of matching rule definitions, ordered by priority (highest first)
        """
        trigger_key = self._make_trigger_key(trigger)
        rule_names = self._trigger_index.get(trigger_key, [])

        # Get the rules and sort by priority (descending)
        rules = [self._rules[name] for name in rule_names if name in self._rules]
        rules.sort(key=lambda r: r.priority, reverse=True)

        return rules

    def get_all(self) -> list[RuleDef]:
        """Get all registered rules.

        Returns:
            List of all rule definitions
        """
        return list(self._rules.values())

    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()
        self._trigger_index.clear()

    def unregister(self, rule_name: str) -> bool:
        """Unregister a rule by name.

        Args:
            rule_name: The name of the rule to unregister

        Returns:
            True if the rule was unregistered, False if not found
        """
        if rule_name not in self._rules:
            return False

        rule = self._rules.pop(rule_name)

        # Remove from trigger index
        trigger_key = self._make_trigger_key(rule.trigger)
        if trigger_key in self._trigger_index:
            if rule_name in self._trigger_index[trigger_key]:
                self._trigger_index[trigger_key].remove(rule_name)

        return True

    def load_from_dsl(self, dsl_content: str) -> list[RuleDef]:
        """Alias for load_from_text for compatibility."""
        parsed = self.load_from_text(dsl_content)
        return [item for item in parsed if isinstance(item, RuleDef)]

    def _register_parsed_items(self, parsed: list[Any]) -> None:
        """Register RuleDef objects from parsed output.

        Args:
            parsed: List of parsed objects
        """
        for item in parsed:
            if isinstance(item, RuleDef):
                try:
                    self.register(item)
                except ValueError:
                    # Rule already registered, skip
                    pass

    def _make_trigger_key(self, trigger: Trigger) -> str:
        """Create a key for trigger indexing.

        Args:
            trigger: The trigger to create a key for

        Returns:
            A string key for indexing
        """
        parts = [trigger.type.value, trigger.entity_type]
        if trigger.property:
            parts.append(trigger.property)
        return ":".join(parts)

    def __len__(self) -> int:
        """Return the number of registered rules."""
        return len(self._rules)

    def __contains__(self, rule_name: str) -> bool:
        """Check if a rule is registered."""
        return rule_name in self._rules
