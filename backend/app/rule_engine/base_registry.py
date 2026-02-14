"""Base registry for rule engine components."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Union
from app.rule_engine.parser import RuleParser
from app.rule_engine.models import ActionDef, RuleDef


class BaseRegistry(ABC):
    """Abstract base class for registries that load DSL definitions."""

    def __init__(self):
        """Initialize with a shared parser."""
        self._parser = RuleParser()

    def load_from_file(
        self, file_path: Union[str, Path]
    ) -> List[Union[ActionDef, RuleDef]]:
        """Load definitions from a DSL file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"DSL file not found: {file_path}")

        parsed = self._parser.parse_file(str(file_path))
        self._register_parsed_items(parsed)
        return parsed

    def load_from_text(self, dsl_text: str) -> List[Union[ActionDef, RuleDef]]:
        """Load definitions from DSL text."""
        parsed = self._parser.parse(dsl_text)
        self._register_parsed_items(parsed)
        return parsed

    @abstractmethod
    def _register_parsed_items(self, parsed: List[Any]) -> None:
        """Actually register relevant items from the parsed AST."""
        pass
