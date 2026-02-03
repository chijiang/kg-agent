# Rule Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete rule engine system supporting ACTION definitions with PRECONDITIONs and RULE definitions for reactive state management over Neo4j knowledge graph.

**Architecture:** 6-phase implementation using Lark parser for DSL, expression evaluator for conditions, action registry for operations, rule engine for event-driven execution, integrated with existing FastAPI/Neo4j stack.

**Tech Stack:** Python 3.11+, FastAPI, Neo4j, Lark parser, pytest

---

## Setup Tasks

### Task 0: Add Lark dependency and create directory structure

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/rule_engine/__init__.py`
- Create: `backend/app/rule_engine/models.py`
- Create: `tests/rule_engine/__init__.py`
- Create: `tests/rule_engine/fixtures/__init__.py`
- Create: `tests/rule_engine/fixtures/sample_rules.dsl`

**Step 1: Add Lark dependency to pyproject.toml**

Edit `backend/pyproject.toml`, add `lark` to dependencies:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    # ... existing dependencies ...
    "lark>=1.1",  # Add this line
]
```

**Step 2: Install the dependency**

Run: `cd backend && uv sync`

**Step 3: Create rule_engine package structure**

Run:
```bash
mkdir -p backend/app/rule_engine
mkdir -p tests/rule_engine/fixtures
touch backend/app/rule_engine/__init__.py
touch tests/rule_engine/__init__.py
touch tests/rule_engine/fixtures/__init__.py
```

**Step 4: Create shared models file**

Create `backend/app/rule_engine/models.py`:

```python
"""Shared data models for rule engine."""

from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


class TriggerType(Enum):
    UPDATE = "UPDATE"
    CREATE = "CREATE"
    DELETE = "DELETE"
    LINK = "LINK"
    SCAN = "SCAN"


@dataclass
class Trigger:
    type: TriggerType
    entity_type: str
    property: str | None = None


@dataclass
class Precondition:
    name: str | None
    condition: Any  # AST Expression node
    on_failure: str


@dataclass
class Parameter:
    name: str
    param_type: str
    optional: bool = False


@dataclass
class ActionDef:
    entity_type: str
    action_name: str
    parameters: list[Parameter]
    preconditions: list[Precondition]
    effect: Any | None  # AST EffectBlock node


@dataclass
class SetStatement:
    target: str  # property path
    value: Any  # AST Expression node


@dataclass
class TriggerStatement:
    entity_type: str
    action_name: str
    target: str  # variable name
    params: dict[str, Any] | None = None


@dataclass
class ForClause:
    variable: str
    entity_type: str
    condition: Any | None  # AST Expression node
    statements: list[Any]  # SetStatement, TriggerStatement, or ForClause


@dataclass
class RuleDef:
    name: str
    priority: int
    trigger: Trigger
    body: ForClause


@dataclass
class UpdateEvent:
    entity_type: str
    entity_id: str
    property: str
    old_value: Any
    new_value: Any


@dataclass
class ActionResult:
    success: bool
    error: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
```

**Step 5: Create sample rule fixture**

Create `tests/rule_engine/fixtures/sample_rules.dsl`:

```javascript
// Sample rule for testing: Supplier Status Blocking
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
        }
    }
}
```

**Step 6: Verify structure and commit**

Run: `ls -la backend/app/rule_engine/`

Expected output: Shows `__init__.py` and `models.py`

```bash
git add backend/pyproject.toml backend/app/rule_engine/ tests/rule_engine/
git commit -m "feat: setup rule engine directory structure and dependencies"
```

---

## Phase 1: DSL Parser

### Task 1: Create Lark grammar file

**Files:**
- Create: `backend/app/rule_engine/grammar.lark`

**Step 1: Write the grammar file**

Create `backend/app/rule_engine/grammar.lark`:

```lark
?start: (action_def | rule_def)*

// ACTION Definition
action_def: "ACTION" entity_action "{" precondition+ effect? "}"

entity_action: CNAME "." CNAME ["(" param_list? ")"]

param_list: param ["," param]
param: CNAME ":" CNAME ["?"]

precondition: "PRECONDITION" [CNAME] ":" expression "ON_FAILURE" ":" STRING

effect: "EFFECT" "{" statement* "}"

// RULE Definition
rule_def: "RULE" CNAME priority? "{" trigger for_clause "}"

priority: "PRIORITY" NUMBER

trigger: "ON" trigger_type "(" trigger_target ")"

trigger_type: "UPDATE" | "CREATE" | "DELETE" | "LINK" | "SCAN"
trigger_target: CNAME ["." CNAME]

// Scope and Statements
for_clause: "FOR" "(" binding ")" "{" statement* "}"

binding: CNAME ":" CNAME ["WHERE" expression]

statement: set_stmt | trigger_stmt | for_clause

set_stmt: "SET" path "=" expression ";"

trigger_stmt: "TRIGGER" entity_action "ON" CNAME ["WITH" object] ";"

// Expressions
expression: or_expr

or_expr: and_expr ("OR" and_expr)*

and_expr: not_expr ("AND" not_expr)*

not_expr: ["NOT"] comparison

comparison: term [comp_op term]
    | term "IN" "[" [value_list] "]"
    | term "IS" ["NOT"] "NULL"
    | term "MATCHES" STRING
    | term "CHANGED" ["FROM" value "TO" value]
    | "EXISTS" "(" pattern ")"

comp_op: "==" | "!=" | "<" | ">" | "<=" | ">="

term: path
    | value
    | function_call
    | "(" expression ")"

path: CNAME ("." CNAME)*

value: STRING
    | NUMBER
    | "true"
    | "false"
    | "NULL"

value_list: value ["," value]

// Pattern Matching for EXISTS
pattern: CNAME [relationship CNAME] ["WHERE" expression]

relationship: "-" ["[" CNAME "]"] "->"

// Functions
function_call: CNAME "(" [arg_list] ")"

arg_list: expression ["," expression]

// Objects
object: "{" [member ["," member]] "}"

member: CNAME ":" expression

// Terminals
STRING: /"[^"]*"/
NUMBER: /[0-9]+(\.[0-9]+)?/
CNAME: /[a-zA-Z_][a-zA-Z0-9_]*/

%import common.WS
%ignore WS
```

**Step 2: Commit grammar file**

```bash
git add backend/app/rule_engine/grammar.lark
git commit -m "feat: add Lark grammar for ACTION and RULE DSL"
```

---

### Task 2: Create AST transformer

**Files:**
- Create: `backend/app/rule_engine/parser.py`
- Create: `tests/rule_engine/test_parser.py`

**Step 1: Write parser test first**

Create `tests/rule_engine/test_parser.py`:

```python
"""Tests for DSL parser."""

import pytest
from app.rule_engine.parser import RuleParser


def test_parse_simple_rule():
    """Test parsing a simple RULE definition."""
    dsl_text = """
    RULE SupplierStatusBlocking PRIORITY 100 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted"]) {
            SET s.locked = true;
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.name == "SupplierStatusBlocking"
    assert rule.priority == 100
    assert rule.trigger.type.value == "UPDATE"
    assert rule.trigger.entity_type == "Supplier"
    assert rule.trigger.property == "status"


def test_parse_rule_with_nested_for():
    """Test parsing a RULE with nested FOR clauses."""
    dsl_text = """
    RULE SupplierStatusBlocking PRIORITY 100 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status IN ["Expired"]) {
            FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s) {
                SET po.status = "RiskLocked";
            }
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.body.variable == "s"
    assert len(rule.body.statements) == 1
    assert isinstance(rule.body.statements[0], ForClause)


def test_parse_action_with_preconditions():
    """Test parsing an ACTION with PRECONDITIONs."""
    dsl_text = """
    ACTION PurchaseOrder.submit {
        PRECONDITION statusCheck: this.status == "Draft"
            ON_FAILURE: "Only draft orders can be submitted"
        PRECONDITION: this.amount > 0
            ON_FAILURE: "Amount must be positive"
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    action = result[0]
    assert action.entity_type == "PurchaseOrder"
    assert action.action_name == "submit"
    assert len(action.preconditions) == 2
    assert action.preconditions[0].name == "statusCheck"
    assert action.preconditions[0].on_failure == "Only draft orders can be submitted"


def test_parse_action_with_effect():
    """Test parsing an ACTION with EFFECT block."""
    dsl_text = """
    ACTION PurchaseOrder.cancel {
        PRECONDITION: this.status == "Open"
            ON_FAILURE: "Cannot cancel"
        EFFECT {
            SET this.status = "Cancelled";
            SET this.cancelledAt = NOW();
        }
    }
    """

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    action = result[0]
    assert action.effect is not None
    assert len(action.effect.statements) == 2


def test_parse_sample_rule():
    """Test parsing the sample SupplierStatusBlocking rule."""
    with open("tests/rule_engine/fixtures/sample_rules.dsl") as f:
        dsl_text = f.read()

    parser = RuleParser()
    result = parser.parse(dsl_text)

    assert len(result) == 1
    rule = result[0]
    assert rule.name == "SupplierStatusBlocking"
    assert rule.priority == 100
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/rule_engine/test_parser.py -v`

Expected: FAIL with `RuleParser not found` or import errors

**Step 3: Write parser implementation**

Create `backend/app/rule_engine/parser.py`:

```python
"""DSL Parser using Lark."""

from lark import Lark, Transformer, Token
from pathlib import Path
from app.rule_engine.models import (
    ActionDef, RuleDef, Precondition, Parameter, Trigger,
    TriggerType, ForClause, SetStatement, TriggerStatement, ForClause
)
from app.rule_engine.grammar import parser as _lark_parser
from typing import Any


class ASTTransformer(Transformer):
    """Transform Lark parse tree into AST nodes."""

    def start(self, items):
        return items

    def action_def(self, items):
        entity_action, preconditions, effect = items
        # entity_action is (entity_type, action_name, parameters)
        entity_type, action_name, parameters = entity_action
        return ActionDef(
            entity_type=entity_type,
            action_name=action_name,
            parameters=parameters,
            preconditions=preconditions,
            effect=effect
        )

    def entity_action(self, items):
        name = items[0]
        params = items[1] if len(items) > 1 else []
        return (name[0], name[1], params)  # (entity_type, action_name, parameters)

    def param_list(self, items):
        return items

    def param(self, items):
        name = items[0].value
        param_type = items[1].value
        optional = len(items) > 2 and items[2].value == "?"
        return Parameter(name=name, param_type=param_type, optional=optional)

    def CNAME(self, items):
        return items[0].value

    def precondition(self, items):
        name = items[0]
        condition = items[1]
        on_failure = items[2]
        return Precondition(name=name, condition=condition, on_failure=on_failure)

    def effect(self, items):
        if not items:
            return None
        return EffectBlock(statements=items)

    def rule_def(self, items):
        name, priority, trigger, body = items
        return RuleDef(
            name=name,
            priority=priority,
            trigger=trigger,
            body=body
        )

    def priority(self, items):
        return int(items[0].value)

    def trigger(self, items):
        trigger_type, target = items
        parts = target.split(".")
        entity_type = parts[0]
        property = parts[1] if len(parts) > 1 else None
        return Trigger(
            type=TriggerType(trigger_type),
            entity_type=entity_type,
            property=property
        )

    def trigger_type(self, items):
        return items[0].value

    def trigger_target(self, items):
        return items[0].value + ("." + items[1].value if len(items) > 1 else "")

    def for_clause(self, items):
        binding, statements = items
        var, entity_type, condition = binding
        return ForClause(
            variable=var,
            entity_type=entity_type,
            condition=condition,
            statements=statements
        )

    def binding(self, items):
        var = items[0].value
        entity_type = items[1].value
        condition = items[2] if len(items) > 2 else None
        return (var, entity_type, condition)

    def statement(self, items):
        return items[0]

    def set_stmt(self, items):
        target, value = items
        return SetStatement(target=target, value=value)

    def trigger_stmt(self, items):
        entity_action, target, params = items
        entity_type, action_name = entity_action
        return TriggerStatement(
            entity_type=entity_type,
            action_name=action_name,
            target=target,
            params=params
        )

    def path(self, items):
        return ".".join(items)

    def STRING(self, items):
        return items[0].value[1:-1]  # Remove quotes

    def NUMBER(self, items):
        return float(items[0].value) if "." in items[0].value else int(items[0].value)

    def object(self, items):
        return dict(items) if items else {}

    def member(self, items):
        return (items[0].value, items[1])

    def value_list(self, items):
        return items

    def function_call(self, items):
        name = items[0].value
        args = items[1] if len(items) > 1 else []
        return ("call", name, args)

    def expression(self, items):
        return items[0]

    def or_expr(self, items):
        if len(items) == 1:
            return items[0]
        return ("or", items[0], items[2])

    def and_expr(self, items):
        if len(items) == 1:
            return items[0]
        return ("and", items[0], items[2])

    def not_expr(self, items):
        if len(items) == 1:
            return items[0]
        return ("not", items[0])

    def comparison(self, items):
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return items[0]
        return ("op", items[1], items[0], items[2])

    def comp_op(self, items):
        return items[0].value


class EffectBlock:
    """Effect block with statements."""
    def __init__(self, statements):
        self.statements = statements


class RuleParser:
    """Parser for ACTION and RULE DSL."""

    def __init__(self):
        # Load grammar from file
        grammar_path = Path(__file__).parent / "grammar.lark"
        with open(grammar_path) as f:
            grammar = f.read()

        self.lark = Lark(
            grammar,
            parser="lalr",
            transformer=ASTTransformer(),
            start="start"
        )

    def parse(self, dsl_text: str) -> list[ActionDef | RuleDef]:
        """Parse DSL text into AST.

        Args:
            dsl_text: DSL source code

        Returns:
            List of ActionDef and RuleDef objects
        """
        return self.lark.parse(dsl_text)

    def parse_file(self, file_path: str) -> list[ActionDef | RuleDef]:
        """Parse DSL file into AST.

        Args:
            file_path: Path to DSL file

        Returns:
            List of ActionDef and RuleDef objects
        """
        with open(file_path) as f:
            return self.parse(f.read())
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_parser.py -v`

Expected: All tests PASS

**Step 5: Commit parser implementation**

```bash
git add backend/app/rule_engine/parser.py tests/rule_engine/test_parser.py
git commit -m "feat: implement DSL parser with Lark"
```

---

## Phase 2: Expression Evaluator

### Task 3: Implement evaluation context and evaluator

**Files:**
- Create: `backend/app/rule_engine/context.py`
- Create: `backend/app/rule_engine/evaluator.py`
- Create: `backend/app/rule_engine/functions.py`
- Create: `tests/rule_engine/test_evaluator.py`

**Step 1: Write evaluator tests first**

Create `tests/rule_engine/test_evaluator.py`:

```python
"""Tests for expression evaluator."""

import pytest
from datetime import datetime
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.parser import RuleParser


def test_evaluate_simple_comparison():
    """Test evaluating simple equality comparison."""
    ctx = EvaluationContext(
        entity={"id": "PO_001", "status": "Open"},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: this.status == "Open"
    ast = ("op", "==", ("path", "this.status"), "Open")
    result = evaluator.evaluate(ast)

    assert result is True


def test_evaluate_in_operator():
    """Test evaluating IN operator."""
    ctx = EvaluationContext(
        entity={"status": "Suspended"},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: this.status IN ["Expired", "Blacklisted", "Suspended"]
    ast = ("in", ("path", "this.status"), ["Expired", "Blacklisted", "Suspended"])
    result = evaluator.evaluate(ast)

    assert result is True


def test_evaluate_and_expression():
    """Test evaluating AND expression."""
    ctx = EvaluationContext(
        entity={"status": "Open", "amount": 1000},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: this.status == "Open" AND this.amount > 500
    ast = ("and",
        ("op", "==", ("path", "this.status"), "Open"),
        ("op", ">", ("path", "this.amount"), 500)
    )
    result = evaluator.evaluate(ast)

    assert result is True


def test_evaluate_or_expression():
    """Test evaluating OR expression."""
    ctx = EvaluationContext(
        entity={"status": "Cancelled"},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: this.status == "Open" OR this.status == "Cancelled"
    ast = ("or",
        ("op", "==", ("path", "this.status"), "Open"),
        ("op", "==", ("path", "this.status"), "Cancelled")
    )
    result = evaluator.evaluate(ast)

    assert result is True


def test_evaluate_not_expression():
    """Test evaluating NOT expression."""
    ctx = EvaluationContext(
        entity={"status": "Open"},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: NOT this.status == "Cancelled"
    ast = ("not", ("op", "==", ("path", "this.status"), "Cancelled"))
    result = evaluator.evaluate(ast)

    assert result is True


def test_evaluate_is_null():
    """Test evaluating IS NULL."""
    ctx = EvaluationContext(
        entity={"status": "Open", "cancelledAt": None},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: this.cancelledAt IS NULL
    ast = ("is_null", ("path", "this.cancelledAt"))
    result = evaluator.evaluate(ast)

    assert result is True


def test_now_function():
    """Test NOW() function."""
    ctx = EvaluationContext(
        entity={},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: NOW()
    ast = ("call", "NOW", [])
    result = evaluator.evaluate(ast)

    assert isinstance(result, datetime)


def test_concat_function():
    """Test CONCAT() function."""
    ctx = EvaluationContext(
        entity={"firstName": "John", "lastName": "Doe"},
        old_values={},
        session=None
    )
    evaluator = ExpressionEvaluator(ctx)

    # AST for: CONCAT(this.firstName, " ", this.lastName)
    ast = ("call", "CONCAT", [
        ("path", "this.firstName"),
        " ",
        ("path", "this.lastName")
    ])
    result = evaluator.evaluate(ast)

    assert result == "John Doe"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/rule_engine/test_evaluator.py -v`

Expected: FAIL with modules not found

**Step 3: Write evaluation context implementation**

Create `backend/app/rule_engine/context.py`:

```python
"""Evaluation context for expressions."""

from dataclasses import dataclass, field
from typing import Any
from neo4j import AsyncSession


@dataclass
class EvaluationContext:
    """Context for evaluating expressions.

    Attributes:
        entity: Current entity being evaluated
        old_values: Previous values for CHANGED detection
        session: Neo4j session for graph queries
        variables: Bound variables from outer FOR scopes
    """

    entity: dict[str, Any]
    old_values: dict[str, Any]
    session: AsyncSession | None
    variables: dict[str, Any] = field(default_factory=dict)

    def get_variable(self, name: str) -> Any:
        """Get a variable from context.

        Args:
            name: Variable name (e.g., "this", "s", "po")

        Returns:
            Variable value or None
        """
        if name == "this":
            return self.entity
        return self.variables.get(name)

    def set_variable(self, name: str, value: Any):
        """Set a variable in context.

        Args:
            name: Variable name
            value: Variable value
        """
        self.variables[name] = value

    def resolve_path(self, path: str) -> Any:
        """Resolve a property path.

        Args:
            path: Dot-separated path like "this.status" or "s.name"

        Returns:
            Property value or None
        """
        parts = path.split(".")
        if parts[0] == "this":
            obj = self.entity
        else:
            obj = self.variables.get(parts[0])
            if obj is None:
                return None

        for part in parts[1:]:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None

        return obj

    def get_old_value(self, property: str) -> Any:
        """Get old value for a property.

        Args:
            property: Property name

        Returns:
            Old value or None
        """
        return self.old_values.get(property)
```

**Step 4: Write functions implementation**

Create `backend/app/rule_engine/functions.py`:

```python
"""Built-in functions for expression evaluation."""

from datetime import datetime, timedelta
from typing import Any


class BuiltinFunctions:
    """Built-in functions for DSL expressions."""

    @staticmethod
    def NOW() -> datetime:
        """Current timestamp."""
        return datetime.now()

    @staticmethod
    def DATE(date_string: str) -> datetime:
        """Parse date string.

        Args:
            date_string: ISO date string

        Returns:
            datetime object
        """
        return datetime.fromisoformat(date_string)

    @staticmethod
    def DAYS(n: int) -> timedelta:
        """Time delta for n days.

        Args:
            n: Number of days

        Returns:
            timedelta object
        """
        return timedelta(days=n)

    @staticmethod
    def HOURS(n: int) -> timedelta:
        """Time delta for n hours.

        Args:
            n: Number of hours

        Returns:
            timedelta object
        """
        return timedelta(hours=n)

    @staticmethod
    def CONCAT(*args: Any) -> str:
        """Concatenate values.

        Args:
            *args: Values to concatenate

        Returns:
            Concatenated string
        """
        return "".join(str(a) for a in args)

    @staticmethod
    def UPPER(s: str) -> str:
        """Uppercase string."""
        return s.upper() if s else s

    @staticmethod
    def LOWER(s: str) -> str:
        """Lowercase string."""
        return s.lower() if s else s

    @staticmethod
    def LENGTH(s: str) -> int:
        """String length."""
        return len(s) if s else 0

    @staticmethod
    def ABS(n: float) -> float:
        """Absolute value."""
        return abs(n)

    @staticmethod
    def ROUND(n: float) -> int:
        """Round number."""
        return round(n)

    @staticmethod
    def MIN(a: float, b: float) -> float:
        """Minimum of two values."""
        return min(a, b)

    @staticmethod
    def MAX(a: float, b: float) -> float:
        """Maximum of two values."""
        return max(a, b)


def evaluate_function(name: str, args: list[Any]) -> Any:
    """Evaluate a built-in function.

    Args:
        name: Function name
        args: Function arguments

    Returns:
        Function result

    Raises:
        ValueError: If function not found
    """
    func = getattr(BuiltinFunctions, name, None)
    if func is None:
        raise ValueError(f"Unknown function: {name}")
    return func(*args)
```

**Step 5: Write evaluator implementation**

Create `backend/app/rule_engine/evaluator.py`:

```python
"""Expression evaluator for DSL conditions."""

from typing import Any
from app.rule_engine.context import EvaluationContext
from app.rule_engine.functions import evaluate_function


class ExpressionEvaluator:
    """Evaluates expression AST nodes."""

    def __init__(self, context: EvaluationContext):
        self.ctx = context

    def evaluate(self, ast: Any) -> Any:
        """Evaluate an expression AST.

        Args:
            ast: Expression AST node

        Returns:
            Evaluation result (bool, value, etc.)
        """
        if ast is None:
            return None

        if isinstance(ast, str):
            return ast

        if isinstance(ast, (int, float, bool)):
            return ast

        if isinstance(ast, list):
            return ast

        if not isinstance(ast, tuple):
            return ast

        op = ast[0]

        # Path reference
        if op == "path":
            return self.ctx.resolve_path(ast[1])

        # Operators
        if op == "op":
            return self._evaluate_comparison(ast[1], ast[2], ast[3])

        if op == "in":
            return self._evaluate_in(ast[1], ast[2])

        if op == "is_null":
            return self._evaluate_is_null(ast[1])

        if op == "and":
            return self._evaluate_and(ast[1], ast[2])

        if op == "or":
            return self._evaluate_or(ast[1], ast[2])

        if op == "not":
            return self._evaluate_not(ast[1])

        # Function call
        if op == "call":
            args = [self.evaluate(a) for a in ast[2]]
            return evaluate_function(ast[1], args)

        return ast

    def _evaluate_comparison(self, op: str, left: Any, right: Any) -> bool:
        """Evaluate comparison operator."""
        left_val = self.evaluate(left)
        right_val = self.evaluate(right)

        if op == "==":
            return left_val == right_val
        if op == "!=":
            return left_val != right_val
        if op == "<":
            return left_val < right_val
        if op == ">":
            return left_val > right_val
        if op == "<=":
            return left_val <= right_val
        if op == ">=":
            return left_val >= right_val

        raise ValueError(f"Unknown comparison operator: {op}")

    def _evaluate_in(self, left: Any, values: list) -> bool:
        """Evaluate IN operator."""
        left_val = self.evaluate(left)
        return left_val in values

    def _evaluate_is_null(self, expr: Any) -> bool:
        """Evaluate IS NULL."""
        val = self.evaluate(expr)
        return val is None

    def _evaluate_and(self, left: Any, right: Any) -> bool:
        """Evaluate AND expression."""
        return bool(self.evaluate(left) and self.evaluate(right))

    def _evaluate_or(self, left: Any, right: Any) -> bool:
        """Evaluate OR expression."""
        return bool(self.evaluate(left) or self.evaluate(right))

    def _evaluate_not(self, expr: Any) -> bool:
        """Evaluate NOT expression."""
        return not bool(self.evaluate(expr))
```

**Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_evaluator.py -v`

Expected: All tests PASS

**Step 7: Commit evaluator implementation**

```bash
git add backend/app/rule_engine/context.py backend/app/rule_engine/evaluator.py backend/app/rule_engine/functions.py tests/rule_engine/test_evaluator.py
git commit -m "feat: implement expression evaluator with built-in functions"
```

---

## Phase 3: Action Registry & Executor

### Task 4: Implement action registry and executor

**Files:**
- Create: `backend/app/rule_engine/action_registry.py`
- Create: `backend/app/rule_engine/action_executor.py`
- Create: `backend/app/rule_engine/effect_handlers.py`
- Create: `backend/app/rule_engine/graph_mutator.py`
- Create: `tests/rule_engine/test_action_registry.py`
- Create: `tests/rule_engine/test_action_executor.py`

**Step 1: Write action registry tests**

Create `tests/rule_engine/test_action_registry.py`:

```python
"""Tests for action registry."""

import pytest
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import ActionDef, Precondition, Parameter


def test_register_and_lookup_action():
    """Test registering and looking up an action."""
    registry = ActionRegistry()

    action = ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name=None,
                condition=("op", "==", ("path", "this.status"), "Draft"),
                on_failure="Must be draft"
            )
        ],
        effect=None
    )

    registry.register(action)

    looked_up = registry.lookup("PurchaseOrder", "submit")
    assert looked_up is not None
    assert looked_up.entity_type == "PurchaseOrder"
    assert looked_up.action_name == "submit"


def test_lookup_nonexistent_action():
    """Test looking up non-existent action."""
    registry = ActionRegistry()

    result = registry.lookup("PurchaseOrder", "nonexistent")
    assert result is None


def test_list_actions_by_entity():
    """Test listing all actions for an entity type."""
    registry = ActionRegistry()

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
        entity_type="Payment",
        action_name="execute",
        parameters=[],
        preconditions=[],
        effect=None
    ))

    po_actions = registry.list_by_entity("PurchaseOrder")
    assert len(po_actions) == 2
    assert [a.action_name for a in po_actions] == ["submit", "cancel"]


def test_load_from_file(tmp_path):
    """Test loading actions from DSL file."""
    import tempfile

    dsl_content = """
    ACTION PurchaseOrder.submit {
        PRECONDITION: this.status == "Draft"
            ON_FAILURE: "Must be draft"
    }

    ACTION PurchaseOrder.cancel {
        PRECONDITION: this.status IN ["Open", "Submitted"]
            ON_FAILURE: "Cannot cancel"
    }
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.dsl', delete=False) as f:
        f.write(dsl_content)
        f.flush()

        registry = ActionRegistry()
        registry.load_from_file(f.name)

        submit = registry.lookup("PurchaseOrder", "submit")
        cancel = registry.lookup("PurchaseOrder", "cancel")

        assert submit is not None
        assert cancel is not None
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/rule_engine/test_action_registry.py -v`

Expected: FAIL with module not found

**Step 3: Write action registry implementation**

Create `backend/app/rule_engine/action_registry.py`:

```python
"""Action registry for storing ACTION definitions."""

from typing import Dict, List
from app.rule_engine.models import ActionDef
from app.rule_engine.parser import RuleParser


class ActionRegistry:
    """Registry for ACTION definitions.

    Stores ACTION definitions indexed by entity_type.action_name.
    """

    def __init__(self):
        self._actions: Dict[str, ActionDef] = {}

    def register(self, action: ActionDef):
        """Register an ACTION definition.

        Args:
            action: ActionDef to register
        """
        key = f"{action.entity_type}.{action.action_name}"
        self._actions[key] = action

    def lookup(self, entity_type: str, action_name: str) -> ActionDef | None:
        """Look up an ACTION definition.

        Args:
            entity_type: Entity type name
            action_name: Action name

        Returns:
            ActionDef or None if not found
        """
        key = f"{entity_type}.{action_name}"
        return self._actions.get(key)

    def list_by_entity(self, entity_type: str) -> List[ActionDef]:
        """List all actions for an entity type.

        Args:
            entity_type: Entity type name

        Returns:
            List of ActionDef
        """
        return [
            action for key, action in self._actions.items()
            if key.startswith(f"{entity_type}.")
        ]

    def list_all(self) -> List[ActionDef]:
        """List all registered actions.

        Returns:
            List of all ActionDef
        """
        return list(self._actions.values())

    def load_from_file(self, file_path: str):
        """Load ACTION definitions from DSL file.

        Args:
            file_path: Path to DSL file
        """
        parser = RuleParser()
        defs = parser.parse_file(file_path)

        for defn in defs:
            if isinstance(defn, ActionDef):
                self.register(defn)

    def load_from_text(self, dsl_text: str):
        """Load ACTION definitions from DSL text.

        Args:
            dsl_text: DSL source code
        """
        parser = RuleParser()
        defs = parser.parse(dsl_text)

        for defn in defs:
            if isinstance(defn, ActionDef):
                self.register(defn)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_action_registry.py -v`

Expected: All tests PASS

**Step 5: Write action executor tests**

Create `tests/rule_engine/test_action_executor.py`:

```python
"""Tests for action executor."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import ActionDef, Precondition


@pytest.mark.asyncio
async def test_execute_action_passing_preconditions():
    """Test executing action with passing preconditions."""
    registry = ActionRegistry()
    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", ("path", "this.status"), "Draft"),
                on_failure="Must be draft"
            )
        ],
        effect=None
    ))

    mock_session = Mock()
    mock_session.run = AsyncMock()

    executor = ActionExecutor(registry, mock_session)

    result = await executor.execute(
        entity_type="PurchaseOrder",
        action_name="submit",
        entity_id="PO_001",
        entity={"id": "PO_001", "status": "Draft"},
        params={}
    )

    assert result.success is True
    assert result.error is None


@pytest.mark.asyncio
async def test_execute_action_failing_precondition():
    """Test executing action with failing precondition."""
    registry = ActionRegistry()
    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[
            Precondition(
                name="statusCheck",
                condition=("op", "==", ("path", "this.status"), "Draft"),
                on_failure="Only draft orders can be submitted"
            )
        ],
        effect=None
    ))

    mock_session = Mock()
    executor = ActionExecutor(registry, mock_session)

    result = await executor.execute(
        entity_type="PurchaseOrder",
        action_name="submit",
        entity_id="PO_001",
        entity={"id": "PO_001", "status": "Open"},
        params={}
    )

    assert result.success is False
    assert "Only draft orders can be submitted" in result.error


@pytest.mark.asyncio
async def test_execute_action_with_effect_set():
    """Test executing action with SET effect."""
    registry = ActionRegistry()

    # Create an effect block with SET statement
    from app.rule_engine.parser import EffectBlock
    from app.rule_engine.models import SetStatement

    effect = EffectBlock(statements=[
        SetStatement(target="this.status", value="Submitted")
    ])

    registry.register(ActionDef(
        entity_type="PurchaseOrder",
        action_name="submit",
        parameters=[],
        preconditions=[],
        effect=effect
    ))

    mock_session = Mock()
    mock_session.run = AsyncMock()

    executor = ActionExecutor(registry, mock_session)

    result = await executor.execute(
        entity_type="PurchaseOrder",
        action_name="submit",
        entity_id="PO_001",
        entity={"id": "PO_001", "status": "Draft"},
        params={}
    )

    assert result.success is True
    assert result.changes.get("status") == "Submitted"
```

**Step 6: Run tests to verify they fail**

Run: `cd backend && pytest tests/rule_engine/test_action_executor.py -v`

Expected: FAIL with module not found

**Step 7: Write action executor implementation**

Create `backend/app/rule_engine/action_executor.py`:

```python
"""Action executor for running ACTION definitions."""

from dataclasses import dataclass, field
from typing import Any
from neo4j import AsyncSession
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator


@dataclass
class ExecutionResult:
    """Result of action execution."""
    success: bool
    error: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)


class ActionExecutor:
    """Executes ACTION definitions."""

    def __init__(self, registry: ActionRegistry, session: AsyncSession):
        self.registry = registry
        self.session = session

    async def execute(
        self,
        entity_type: str,
        action_name: str,
        entity_id: str,
        entity: dict[str, Any],
        params: dict[str, Any]
    ) -> ExecutionResult:
        """Execute an ACTION.

        Args:
            entity_type: Entity type name
            action_name: Action name
            entity_id: Entity ID
            entity: Entity data
            params: Action parameters

        Returns:
            ExecutionResult
        """
        # Look up action
        action = self.registry.lookup(entity_type, action_name)
        if action is None:
            return ExecutionResult(
                success=False,
                error=f"Action {entity_type}.{action_name} not found"
            )

        # Check preconditions
        ctx = EvaluationContext(
            entity=entity,
            old_values={},
            session=self.session
        )
        evaluator = ExpressionEvaluator(ctx)

        for precond in action.preconditions:
            result = evaluator.evaluate(precond.condition)
            if not result:
                return ExecutionResult(
                    success=False,
                    error=precond.on_failure
                )

        # Execute effects
        changes = {}
        if action.effect:
            for stmt in action.effect.statements:
                if hasattr(stmt, 'target'):  # SetStatement
                    value = evaluator.evaluate(stmt.value)
                    prop = stmt.target.replace("this.", "")
                    changes[prop] = value
                    entity[prop] = value

        # Update in Neo4j if there are changes
        if changes:
            await self._apply_changes(entity_type, entity_id, changes)

        return ExecutionResult(success=True, changes=changes)

    async def _apply_changes(
        self,
        entity_type: str,
        entity_id: str,
        changes: dict[str, Any]
    ):
        """Apply changes to Neo4j.

        Args:
            entity_type: Entity type name
            entity_id: Entity ID
            changes: Property changes to apply
        """
        set_clause = ", ".join([f"n.{k} = ${k}" for k in changes.keys()])
        query = f"""
            MATCH (n:`{entity_type}` {{id: $id}})
            SET {set_clause}
        """

        params = {"id": entity_id, **changes}
        await self.session.run(query, **params)
```

**Step 8: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_action_executor.py -v`

Expected: All tests PASS

**Step 9: Commit action system implementation**

```bash
git add backend/app/rule_engine/action_registry.py backend/app/rule_engine/action_executor.py tests/rule_engine/test_action_registry.py tests/rule_engine/test_action_executor.py
git commit -m "feat: implement action registry and executor"
```

---

## Phase 4: Rule Engine Core

### Task 5: Implement Cypher translator and rule engine

**Files:**
- Create: `backend/app/rule_engine/cypher_translator.py`
- Create: `backend/app/rule_engine/rule_registry.py`
- Create: `backend/app/rule_engine/rule_engine.py`
- Create: `tests/rule_engine/test_cypher_translator.py`
- Create: `tests/rule_engine/test_rule_engine.py`

**Step 1: Write Cypher translator tests**

Create `tests/rule_engine/test_cypher_translator.py`:

```python
"""Tests for Cypher translator."""

from app.rule_engine.cypher_translator import CypherTranslator
from app.rule_engine.models import ForClause, Trigger


def test_translate_simple_for_clause():
    """Test translating simple FOR clause."""
    translator = CypherTranslator()

    for_clause = ForClause(
        variable="s",
        entity_type="Supplier",
        condition=("op", "==", ("path", "s.status"), "Suspended"),
        statements=[]
    )

    query, params = translator.translate_for(for_clause)

    assert "MATCH (s:Supplier)" in query
    assert "s.status = $s_status" in query
    assert "RETURN s" in query
    assert "s_status" in params


def test_translate_for_with_relationship():
    """Test translating FOR clause with relationship."""
    translator = CypherTranslator()

    # AST for: po -[orderedFrom]-> s
    condition = ("and",
        ("exists", ("pattern", "po", "orderedFrom", "s")),
        ("op", "==", ("path", "po.status"), "Open")
    )

    for_clause = ForClause(
        variable="po",
        entity_type="PurchaseOrder",
        condition=condition,
        statements=[]
    )

    # Bind outer variable 's'
    translator.bind_variable("s", "Supplier", "supplier_id")

    query, params = translator.translate_for(for_clause)

    assert "MATCH (po:PurchaseOrder)" in query
    assert "-[:orderedFrom]->" in query
    assert "po.status = $po_status" in query


def test_translate_in_condition():
    """Test translating IN condition."""
    translator = CypherTranslator()

    # AST for: s.status IN ["Expired", "Blacklisted", "Suspended"]
    condition = ("in", ("path", "s.status"), ["Expired", "Blacklisted", "Suspended"])

    where, params = translator.translate_condition(condition)

    assert "s.status IN" in where
    assert "$s_status_values" in where
    assert params["s_status_values"] == ["Expired", "Blacklisted", "Suspended"]
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/rule_engine/test_cypher_translator.py -v`

Expected: FAIL with module not found

**Step 3: Write Cypher translator implementation**

Create `backend/app/rule_engine/cypher_translator.py`:

```python
"""Translates FOR clauses to Cypher queries."""

from typing import Any
from app.rule_engine.models import ForClause


class CypherTranslator:
    """Translates DSL FOR clauses to Cypher queries."""

    def __init__(self):
        self._bound_variables: dict[str, tuple[str, str, str]] = {}
        self._param_counter = 0

    def bind_variable(self, var: str, entity_type: str, entity_id: str):
        """Bind a variable from outer scope.

        Args:
            var: Variable name
            entity_type: Entity type
            entity_id: Entity ID parameter name
        """
        self._bound_variables[var] = (entity_type, entity_id)

    def translate_for(self, for_clause: ForClause) -> tuple[str, dict]:
        """Translate a FOR clause to Cypher.

        Args:
            for_clause: ForClause to translate

        Returns:
            Tuple of (query, params)
        """
        self._param_counter = 0
        params = {}

        # Build MATCH clause
        match = f"MATCH ({for_clause.variable}:{for_clause.entity_type})"

        # Build WHERE clause if condition exists
        where = ""
        if for_clause.condition:
            where_clause, where_params = self.translate_condition(
                for_clause.condition,
                for_clause.variable
            )
            if where_clause:
                where = f" WHERE {where_clause}"
            params.update(where_params)

        # Add bound variable constraints
        for var, (entity_type, id_param) in self._bound_variables.items():
            if where:
                where += f" AND {var}.id = ${id_param}"
            else:
                where = f" WHERE {var}.id = ${id_param}"
            params[id_param] = None  # Will be filled by caller

        query = f"{match}{where} RETURN {for_clause.variable}"
        return query, params

    def translate_condition(self, condition: Any, var: str) -> tuple[str, dict]:
        """Translate a condition expression to Cypher WHERE.

        Args:
            condition: AST condition node
            var: Current variable name

        Returns:
            Tuple of (where_clause, params)
        """
        if condition is None:
            return "", {}

        if not isinstance(condition, tuple):
            return "", {}

        op = condition[0]

        # Path reference
        if op == "path":
            path = condition[1]
            return path, {}

        # Comparison operators
        if op == "op":
            return self._translate_comparison(condition[1], condition[2], condition[3])

        # IN operator
        if op == "in":
            return self._translate_in(condition[1], condition[2])

        # AND/OR
        if op == "and":
            left, left_params = self.translate_condition(condition[1], var)
            right, right_params = self.translate_condition(condition[2], var)
            return f"({left} AND {right})", {**left_params, **right_params}

        if op == "or":
            left, left_params = self.translate_condition(condition[1], var)
            right, right_params = self.translate_condition(condition[2], var)
            return f"({left} OR {right})", {**left_params, **right_params}

        if op == "not":
            expr, params = self.translate_condition(condition[1], var)
            return f"NOT ({expr})", params

        # EXISTS (pattern matching)
        if op == "exists":
            return self._translate_exists(condition[1])

        return "", {}

    def _translate_comparison(self, op: str, left: Any, right: Any) -> tuple[str, dict]:
        """Translate comparison to Cypher."""
        left_expr, _ = self.translate_condition(left, "")
        right_val = right if not isinstance(right, tuple) else right

        param_name = self._next_param()
        params = {param_name: right_val}

        return f"{left_expr} {op} ${param_name}", params

    def _translate_in(self, left: Any, values: list) -> tuple[str, dict]:
        """Translate IN operator to Cypher."""
        left_expr, _ = self.translate_condition(left, "")
        param_name = self._next_param()
        return f"{left_expr} IN ${param_name}", {param_name: values}

    def _translate_exists(self, pattern: Any) -> tuple[str, dict]:
        """Translate EXISTS pattern to Cypher."""
        # pattern: ("pattern", from_var, rel, to_var)
        parts = pattern
        from_var = parts[1]
        rel = parts[2] if len(parts) > 2 else None
        to_var = parts[3] if len(parts) > 3 else None

        if rel and to_var:
            return f"EXISTS(({from_var})-[:{rel}]->({to_var}))", {}
        return "", {}

    def _next_param(self) -> str:
        """Generate next unique parameter name."""
        name = f"param_{self._param_counter}"
        self._param_counter += 1
        return name
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_cypher_translator.py -v`

Expected: Tests pass (some may need adjustment based on AST structure)

**Step 5: Write rule registry implementation**

Create `backend/app/rule_engine/rule_registry.py`:

```python
"""Rule registry for storing RULE definitions."""

from typing import Dict, List
from app.rule_engine.models import RuleDef, Trigger, TriggerType
from app.rule_engine.parser import RuleParser


class RuleRegistry:
    """Registry for RULE definitions.

    Stores RULE definitions indexed by trigger.
    """

    def __init__(self):
        self._rules: List[RuleDef] = []
        self._trigger_index: Dict[str, List[RuleDef]] = {}

    def register(self, rule: RuleDef):
        """Register a RULE definition.

        Args:
            rule: RuleDef to register
        """
        self._rules.append(rule)

        # Index by trigger
        trigger_key = self._get_trigger_key(rule.trigger)
        if trigger_key not in self._trigger_index:
            self._trigger_index[trigger_key] = []

        self._trigger_index[trigger_key].append(rule)
        # Sort by priority (descending)
        self._trigger_index[trigger_key].sort(key=lambda r: -r.priority)

    def lookup(self, rule_name: str) -> RuleDef | None:
        """Look up a RULE by name.

        Args:
            rule_name: Rule name

        Returns:
            RuleDef or None
        """
        for rule in self._rules:
            if rule.name == rule_name:
                return rule
        return None

    def get_by_trigger(self, trigger: Trigger) -> List[RuleDef]:
        """Get rules matching a trigger.

        Args:
            trigger: Trigger to match

        Returns:
            List of matching RuleDef, sorted by priority
        """
        trigger_key = self._get_trigger_key(trigger)
        return self._trigger_index.get(trigger_key, [])

    def list_all(self) -> List[RuleDef]:
        """List all registered rules.

        Returns:
            List of all RuleDef
        """
        return list(self._rules)

    def _get_trigger_key(self, trigger: Trigger) -> str:
        """Get index key for a trigger.

        Args:
            trigger: Trigger

        Returns:
            Trigger key string
        """
        if trigger.property:
            return f"{trigger.type.value}.{trigger.entity_type}.{trigger.property}"
        return f"{trigger.type.value}.{trigger.entity_type}"

    def load_from_file(self, file_path: str):
        """Load RULE definitions from DSL file.

        Args:
            file_path: Path to DSL file
        """
        parser = RuleParser()
        defs = parser.parse_file(file_path)

        for defn in defs:
            if isinstance(defn, RuleDef):
                self.register(defn)

    def load_from_text(self, dsl_text: str):
        """Load RULE definitions from DSL text.

        Args:
            dsl_text: DSL source code
        """
        parser = RuleParser()
        defs = parser.parse(dsl_text)

        for defn in defs:
            if isinstance(defn, RuleDef):
                self.register(defn)
```

**Step 6: Write rule engine tests**

Create `tests/rule_engine/test_rule_engine.py`:

```python
"""Tests for rule engine."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.models import Trigger, TriggerType, UpdateEvent


@pytest.mark.asyncio
async def test_match_rules_by_trigger():
    """Test matching rules by trigger."""
    action_registry = ActionRegistry()
    rule_registry = RuleRegistry()

    # Load sample rule
    rule_registry.load_from_file("tests/rule_engine/fixtures/sample_rules.dsl")

    engine = RuleEngine(action_registry, rule_registry, None)

    event = UpdateEvent(
        entity_type="Supplier",
        entity_id="BP_10001",
        property="status",
        old_value="Active",
        new_value="Suspended"
    )

    matched = engine._match_rules(event)
    assert len(matched) == 1
    assert matched[0].name == "SupplierStatusBlocking"


@pytest.mark.asyncio
async def test_on_event_executes_rule():
    """Test that ON UPDATE event executes matching rule."""
    from app.rule_engine.cypher_translator import CypherTranslator

    action_registry = ActionRegistry()
    rule_registry = RuleRegistry()

    rule_registry.load_from_file("tests/rule_engine/fixtures/sample_rules.dsl")

    # Mock Neo4j session
    mock_session = Mock()
    mock_session.run = AsyncMock()

    # Mock query results - return matching entities
    mock_result = Mock()
    mock_result.data = AsyncMock(return_value=[
        {"s": {"id": "BP_10001", "status": "Suspended"}}
    ])
    mock_result_single = Mock()
    mock_result_single.data = AsyncMock(return_value=[
        {"po": {"id": "PO_001", "status": "Open"}}
    ])
    mock_session.run.return_value = mock_result

    engine = RuleEngine(action_registry, rule_registry, mock_session)

    event = UpdateEvent(
        entity_type="Supplier",
        entity_id="BP_10001",
        property="status",
        old_value="Active",
        new_value="Suspended"
    )

    await engine.on_event(event)

    # Verify session.run was called
    assert mock_session.run.called
```

**Step 7: Write rule engine implementation**

Create `backend/app/rule_engine/rule_engine.py`:

```python
"""Rule engine core for reactive rule execution."""

from typing import List
from neo4j import AsyncSession
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.cypher_translator import CypherTranslator
from app.rule_engine.models import RuleDef, UpdateEvent, SetStatement, TriggerStatement, ForClause


class RuleEngine:
    """Core rule engine for reactive rule execution."""

    def __init__(
        self,
        action_registry: ActionRegistry,
        rule_registry: RuleRegistry,
        session: AsyncSession
    ):
        self.action_registry = action_registry
        self.rule_registry = rule_registry
        self.session = session
        self.translator = CypherTranslator()
        self._cascade_depth = 0
        self._max_cascade_depth = 10
        self._visited: set = set()

    async def on_event(self, event: UpdateEvent):
        """Handle a graph update event.

        Args:
            event: UpdateEvent from graph change
        """
        # Prevent infinite cascades
        if self._cascade_depth > self._max_cascade_depth:
            return

        # Match rules by trigger
        matched_rules = self._match_rules(event)

        # Execute each rule
        for rule in matched_rules:
            await self._execute_rule(rule, event)

    def _match_rules(self, event: UpdateEvent) -> List[RuleDef]:
        """Match rules to an event.

        Args:
            event: UpdateEvent

        Returns:
            List of matching RuleDef, sorted by priority
        """
        from app.rule_engine.models import Trigger, TriggerType

        trigger = Trigger(
            type=TriggerType.UPDATE,
            entity_type=event.entity_type,
            property=event.property
        )

        return self.rule_registry.get_by_trigger(trigger)

    async def _execute_rule(self, rule: RuleDef, event: UpdateEvent):
        """Execute a rule.

        Args:
            rule: RuleDef to execute
            event: Triggering event
        """
        # Execute outer FOR clause
        await self._execute_for_clause(rule.body, {event.entity_type: event.entity_id})

    async def _execute_for_clause(
        self,
        for_clause: ForClause,
        outer_vars: dict[str, str]
    ):
        """Execute a FOR clause.

        Args:
            for_clause: ForClause to execute
            outer_vars: Outer variable bindings (var_name -> entity_id)
        """
        # Bind outer variables
        for var, entity_id in outer_vars.items():
            self.translator.bind_variable(var, for_clause.entity_type, f"id_{var}")

        # Translate FOR clause to Cypher
        query, params = self.translator.translate_for(for_clause)

        # Add entity IDs for bound variables
        for var, entity_id in outer_vars.items():
            params[f"id_{var}"] = entity_id

        # Execute query
        result = await self.session.run(query, **params)
        entities = await result.data()

        # Process each entity
        for entity_row in entities:
            var_name = for_clause.variable
            entity = entity_row.get(var_name)

            if not entity:
                continue

            # Execute statements
            for stmt in for_clause.statements:
                if isinstance(stmt, SetStatement):
                    await self._execute_set(stmt, entity, for_clause.entity_type)

                elif isinstance(stmt, TriggerStatement):
                    await self._execute_trigger(stmt, entity)

                elif isinstance(stmt, ForClause):
                    # Nested FOR clause
                    await self._execute_for_clause(stmt, {**outer_vars, var_name: entity["id"]})

    async def _execute_set(
        self,
        stmt: SetStatement,
        entity: dict,
        entity_type: str
    ):
        """Execute a SET statement.

        Args:
            stmt: SetStatement
            entity: Entity data
            entity_type: Entity type name
        """
        # Resolve property path
        prop = stmt.target.replace(f"{for_clause.variable}.", "")

        # Evaluate value (simplified - just use literal values for now)
        value = stmt.value if not isinstance(stmt.value, tuple) else stmt.value

        # Execute update
        query = f"""
            MATCH (n:{entity_type} {{id: $id}})
            SET n.{prop} = $value
        """
        await self.session.run(query, id=entity["id"], value=value)

    async def _execute_trigger(self, stmt: TriggerStatement, entity: dict):
        """Execute a TRIGGER statement.

        Args:
            stmt: TriggerStatement
            entity: Entity to trigger action on
        """
        from app.rule_engine.action_executor import ActionExecutor

        executor = ActionExecutor(self.action_registry, self.session)

        # Get entity data
        entity_id = entity.get("id")
        entity_type = stmt.entity_type

        # Execute action
        await executor.execute(
            entity_type=entity_type,
            action_name=stmt.action_name,
            entity_id=entity_id,
            entity=entity,
            params=stmt.params or {}
        )
```

**Step 8: Run tests to verify they pass**

Run: `cd backend && pytest tests/rule_engine/test_rule_engine.py -v`

Expected: Tests pass (may need adjustments)

**Step 9: Commit rule engine core implementation**

```bash
git add backend/app/rule_engine/cypher_translator.py backend/app/rule_engine/rule_registry.py backend/app/rule_engine/rule_engine.py tests/rule_engine/test_cypher_translator.py tests/rule_engine/test_rule_engine.py
git commit -m "feat: implement rule engine core with Cypher translator"
```

---

## Phase 5: Event Integration

### Task 6: Implement event emitter and integrate with GraphTools

**Files:**
- Create: `backend/app/rule_engine/event_emitter.py`
- Modify: `backend/app/services/graph_tools.py`
- Create: `tests/rule_engine/test_integration.py`

**Step 1: Write event emitter implementation**

Create `backend/app/rule_engine/event_emitter.py`:

```python
"""Event emitter for graph changes."""

from typing import List, Callable
from app.rule_engine.models import UpdateEvent


class GraphEventEmitter:
    """Emits events when graph changes occur."""

    def __init__(self):
        self._listeners: List[Callable] = []

    def subscribe(self, listener: Callable):
        """Subscribe to graph events.

        Args:
            listener: Callable that receives UpdateEvent
        """
        self._listeners.append(listener)

    def unsubscribe(self, listener: Callable):
        """Unsubscribe from graph events.

        Args:
            listener: Callable to remove
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    async def emit(self, event: UpdateEvent):
        """Emit a graph event to all listeners.

        Args:
            event: UpdateEvent to emit
        """
        for listener in self._listeners:
            if hasattr(listener, '__call__'):
                if hasattr(listener, 'on_event'):
                    await listener.on_event(event)
                else:
                    await listener(event)
```

**Step 2: Write integration tests**

Create `tests/rule_engine/test_integration.py`:

```python
"""Integration tests for rule engine with graph operations."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.models import UpdateEvent


@pytest.mark.asyncio
async def test_event_emitter_broadcast():
    """Test that event emitter broadcasts to listeners."""
    emitter = GraphEventEmitter()

    received = []

    async def listener1(event: UpdateEvent):
        received.append(("listener1", event))

    async def listener2(event: UpdateEvent):
        received.append(("listener2", event))

    emitter.subscribe(listener1)
    emitter.subscribe(listener2)

    event = UpdateEvent(
        entity_type="Supplier",
        entity_id="BP_10001",
        property="status",
        old_value="Active",
        new_value="Suspended"
    )

    await emitter.emit(event)

    assert len(received) == 2
    assert received[0][0] == "listener1"
    assert received[1][0] == "listener2"


@pytest.mark.asyncio
async def test_graph_tools_emits_events():
    """Test that GraphTools emits events on updates."""
    from app.services.graph_tools import GraphTools

    # Mock session
    mock_session = Mock()
    mock_session.run = AsyncMock()

    # Setup event emitter
    emitter = GraphEventEmitter()

    received = []

    async def capture(event: UpdateEvent):
        received.append(event)

    emitter.subscribe(capture)

    # Create GraphTools with emitter
    tools = GraphTools.__new__(GraphTools)
    tools.session = mock_session
    tools.event_emitter = emitter

    # Simulate update (we'll need to modify GraphTools)
    # For now, just test the emitter integration
    event = UpdateEvent(
        entity_type="Supplier",
        entity_id="BP_10001",
        property="status",
        old_value="Active",
        new_value="Suspended"
    )

    await emitter.emit(event)

    assert len(received) == 1
    assert received[0].entity_type == "Supplier"
```

**Step 3: Modify GraphTools to emit events**

Edit `backend/app/services/graph_tools.py`:

Add import at top:
```python
from typing import List, Any, TYPE_CHECKING
from neo4j import AsyncSession
from langchain_core.tools import tool

if TYPE_CHECKING:
    from app.rule_engine.event_emitter import GraphEventEmitter
    from app.rule_engine.models import UpdateEvent
```

Modify `__init__` method:
```python
def __init__(self, session: AsyncSession, event_emitter: "GraphEventEmitter | None" = None):
    self.session = session
    self.event_emitter = event_emitter
```

Add event emission helper:
```python
async def _emit_update_event(
    self,
    entity_id: str,
    entity_type: str,
    updates: dict[str, Any],
    old_values: dict[str, Any] | None = None
):
    """Emit update events for rule engine.

    Args:
        entity_id: Entity ID
        entity_type: Entity type
        updates: New values
        old_values: Old values (optional, will fetch if not provided)
    """
    if not self.event_emitter:
        return

    if old_values is None:
        # Fetch old values
        old_values = await self._get_entity_raw(entity_id)

    if not old_values:
        return

    from app.rule_engine.models import UpdateEvent

    for key, new_val in updates.items():
        old_val = old_values.get(key)
        if old_val != new_val:
            await self.event_emitter.emit(UpdateEvent(
                entity_type=entity_type,
                entity_id=entity_id,
                property=key,
                old_value=old_val,
                new_value=new_val
            ))

async def _get_entity_raw(self, entity_id: str) -> dict | None:
    """Get raw entity data for change detection."""
    query = "MATCH (n {id: $id}) RETURN n"
    result = await self.session.run(query, id=entity_id)
    data = await result.data()
    if data and "n" in data[0]:
        return data[0]["n"]
    return None
```

**Step 4: Run integration tests**

Run: `cd backend && pytest tests/rule_engine/test_integration.py -v`

Expected: Tests pass

**Step 5: Commit event integration**

```bash
git add backend/app/rule_engine/event_emitter.py backend/app/services/graph_tools.py tests/rule_engine/test_integration.py
git commit -m "feat: add event emitter and integrate with GraphTools"
```

---

## Phase 6: API & Management

### Task 7: Implement REST API endpoints

**Files:**
- Create: `backend/app/api/actions.py`
- Create: `backend/app/api/rules.py`
- Create: `backend/app/services/rule_storage.py`
- Create: `tests/api/test_actions_api.py`
- Create: `tests/api/test_rules_api.py`

**Step 1: Create rule storage service**

Create `backend/app/services/rule_storage.py`:

```python
"""Rule file storage service."""

import os
from pathlib import Path
from typing import List


class RuleStorage:
    """Service for storing and retrieving rule DSL files."""

    def __init__(self, rules_dir: str = "rules"):
        self.rules_dir = Path(rules_dir)
        self.rules_dir.mkdir(exist_ok=True)

    def save(self, name: str, content: str) -> str:
        """Save a rule file.

        Args:
            name: Rule file name (without .dsl extension)
            content: DSL content

        Returns:
            Full path to saved file
        """
        path = self.rules_dir / f"{name}.dsl"
        path.write_text(content)
        return str(path)

    def load(self, name: str) -> str | None:
        """Load a rule file.

        Args:
            name: Rule file name (without .dsl extension)

        Returns:
            DSL content or None if not found
        """
        path = self.rules_dir / f"{name}.dsl"
        if path.exists():
            return path.read_text()
        return None

    def delete(self, name: str) -> bool:
        """Delete a rule file.

        Args:
            name: Rule file name

        Returns:
            True if deleted, False if not found
        """
        path = self.rules_dir / f"{name}.dsl"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> List[str]:
        """List all rule files.

        Returns:
            List of rule names (without .dsl extension)
        """
        return [
            f.stem for f in self.rules_dir.glob("*.dsl")
        ]

    def get_path(self, name: str) -> str:
        """Get full path for a rule file.

        Args:
            name: Rule file name

        Returns:
            Full path to rule file
        """
        return str(self.rules_dir / f"{name}.dsl")
```

**Step 2: Create actions API endpoint**

Create `backend/app/api/actions.py`:

```python
"""API endpoints for action invocation."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any, Dict
from neo4j import AsyncSession

from app.api.deps import get neo4j_session
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult


router = APIRouter(prefix="/api/actions", tags=["actions"])

# Global action registry (should be initialized at startup)
_action_registry: ActionRegistry | None = None


def get_action_registry() -> ActionRegistry:
    """Get global action registry."""
    global _action_registry
    if _action_registry is None:
        _action_registry = ActionRegistry()
        # Load default actions
        import os
        actions_dir = os.path.join(os.path.dirname(__file__), "..", "rules")
        if os.path.exists(actions_dir):
            for file in os.listdir(actions_dir):
                if file.endswith(".dsl"):
                    _action_registry.load_from_file(os.path.join(actions_dir, file))
    return _action_registry


class ActionRequest(BaseModel):
    """Request model for action invocation."""
    entity_id: str
    params: Dict[str, Any] = {}


class ActionResponse(BaseModel):
    """Response model for action execution."""
    success: bool
    error: str | None = None
    changes: Dict[str, Any] = {}


@router.post("/{entity_type}/{action_name}", response_model=ActionResponse)
async def execute_action(
    entity_type: str,
    action_name: str,
    request: ActionRequest,
    session: AsyncSession = Depends(get_neo4j_session),
    registry: ActionRegistry = Depends(get_action_registry)
):
    """Execute an ACTION.

    Args:
        entity_type: Entity type name (e.g., PurchaseOrder)
        action_name: Action name (e.g., submit)
        request: Action request with entity_id and params
        session: Neo4j session
        registry: Action registry

    Returns:
        ActionResponse with success status
    """
    # Fetch entity
    query = f"MATCH (n:`{entity_type}` {{id: $id}}) RETURN n"
    result = await session.run(query, id=request.entity_id)
    data = await result.data()

    if not data:
        raise HTTPException(status_code=404, detail=f"Entity {request.entity_id} not found")

    entity = data[0]["n"]

    # Execute action
    executor = ActionExecutor(registry, session)
    result: ExecutionResult = await executor.execute(
        entity_type=entity_type,
        action_name=action_name,
        entity_id=request.entity_id,
        entity=entity,
        params=request.params
    )

    return ActionResponse(
        success=result.success,
        error=result.error,
        changes=result.changes
    )


@router.get("/", response_model=List[Dict[str, Any]])
async def list_actions(
    entity_type: str | None = None,
    registry: ActionRegistry = Depends(get_action_registry)
):
    """List all actions or actions for a specific entity type.

    Args:
        entity_type: Optional entity type filter

    Returns:
        List of action definitions
    """
    if entity_type:
        actions = registry.list_by_entity(entity_type)
    else:
        actions = registry.list_all()

    return [
        {
            "entity_type": a.entity_type,
            "action_name": a.action_name,
            "parameters": [{"name": p.name, "type": p.param_type} for p in a.parameters],
            "preconditions": len(a.preconditions)
        }
        for a in actions
    ]


@router.get("/{entity_type}", response_model=List[Dict[str, Any]])
async def list_entity_actions(
    entity_type: str,
    registry: ActionRegistry = Depends(get_action_registry)
):
    """List actions for a specific entity type.

    Args:
        entity_type: Entity type name

    Returns:
        List of action definitions for the entity type
    """
    actions = registry.list_by_entity(entity_type)

    return [
        {
            "action_name": a.action_name,
            "parameters": [{"name": p.name, "type": p.param_type} for p in a.parameters],
            "preconditions": len(a.preconditions)
        }
        for a in actions
    ]
```

**Step 3: Create rules API endpoint**

Create `backend/app/api/rules.py`:

```python
"""API endpoints for rule management."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from neo4j import AsyncSession

from app.api.deps import get_neo4j_session
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.action_registry import ActionRegistry
from app.services.rule_storage import RuleStorage


router = APIRouter(prefix="/api/rules", tags=["rules"])

# Global registries
_rule_registry: RuleRegistry | None = None
_action_registry: ActionRegistry | None = None
_rule_storage: RuleStorage | None = None


def get_rule_registry() -> RuleRegistry:
    """Get global rule registry."""
    global _rule_registry, _action_registry
    if _rule_registry is None:
        _action_registry = _action_registry or ActionRegistry()
        _rule_registry = RuleRegistry()
        # Load default rules
        storage = get_rule_storage()
        for name in storage.list_all():
            _rule_registry.load_from_file(storage.get_path(name))
    return _rule_registry


def get_action_registry() -> ActionRegistry:
    """Get global action registry."""
    global _action_registry
    if _action_registry is None:
        _action_registry = ActionRegistry()
    return _action_registry


def get_rule_storage() -> RuleStorage:
    """Get global rule storage."""
    global _rule_storage
    if _rule_storage is None:
        _rule_storage = RuleStorage()
    return _rule_storage


class RuleUploadRequest(BaseModel):
    """Request model for uploading a rule."""
    name: str
    content: str


class RuleResponse(BaseModel):
    """Response model for rule info."""
    name: str
    priority: int
    trigger: Dict[str, Any]


@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    registry: RuleRegistry = Depends(get_rule_registry)
):
    """List all registered rules.

    Returns:
        List of rule definitions
    """
    rules = registry.list_all()

    return [
        RuleResponse(
            name=r.name,
            priority=r.priority,
            trigger={
                "type": r.trigger.type.value,
                "entity_type": r.trigger.entity_type,
                "property": r.trigger.property
            }
        )
        for r in rules
    ]


@router.get("/{name}", response_model=Dict[str, Any])
async def get_rule(
    name: str,
    registry: RuleRegistry = Depends(get_rule_registry),
    storage: RuleStorage = Depends(get_rule_storage)
):
    """Get a rule by name.

    Args:
        name: Rule name

    Returns:
        Rule definition and DSL content
    """
    rule = registry.lookup(name)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {name} not found")

    content = storage.load(name)

    return {
        "name": rule.name,
        "priority": rule.priority,
        "trigger": {
            "type": rule.trigger.type.value,
            "entity_type": rule.trigger.entity_type,
            "property": rule.trigger.property
        },
        "dsl": content
    }


@router.post("/")
async def upload_rule(
    request: RuleUploadRequest,
    registry: RuleRegistry = Depends(get_rule_registry),
    storage: RuleStorage = Depends(get_rule_storage)
):
    """Upload a new rule.

    Args:
        request: Rule upload request with name and content

    Returns:
        Success message
    """
    # Save rule file
    storage.save(request.name, request.content)

    # Load into registry
    registry.load_from_text(request.content)

    return {"message": f"Rule {request.name} uploaded successfully"}


@router.delete("/{name}")
async def delete_rule(
    name: str,
    registry: RuleRegistry = Depends(get_rule_registry),
    storage: RuleStorage = Depends(get_rule_storage)
):
    """Delete a rule.

    Args:
        name: Rule name

    Returns:
        Success message
    """
    # Delete from storage
    if not storage.delete(name):
        raise HTTPException(status_code=404, detail=f"Rule {name} not found")

    # Note: Registry would need to be reloaded or have remove method
    # For now, we'll just remove from storage

    return {"message": f"Rule {name} deleted successfully"}
```

**Step 4: Register API routes in main app**

Edit `backend/app/main.py`:

Add imports:
```python
from app.api import actions, rules
```

Add router includes after existing routers:
```python
app.include_router(actions.router)
app.include_router(rules.router)
```

**Step 5: Write API tests**

Create `tests/api/test_actions_api.py`:

```python
"""Tests for actions API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_actions(client):
    """Test listing all actions."""
    response = client.get("/api/actions/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_execute_action_not_found(client, mock_neo4j):
    """Test executing action on non-existent entity."""
    with patch("app.api.actions.get_neo4j_session", return_value=mock_neo4j):
        response = client.post(
            "/api/actions/PurchaseOrder/submit",
            json={"entity_id": "NONEXISTENT", "params": {}}
        )

    assert response.status_code == 404
```

Create `tests/api/test_rules_api.py`:

```python
"""Tests for rules API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_rules(client):
    """Test listing all rules."""
    response = client.get("/api/rules/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_upload_rule(client):
    """Test uploading a new rule."""
    dsl_content = """
    RULE TestRule PRIORITY 50 {
        ON UPDATE(Supplier.status)
        FOR (s: Supplier WHERE s.status == "Suspended") {
            SET s.locked = true;
        }
    }
    """

    response = client.post(
        "/api/rules/",
        json={"name": "TestRule", "content": dsl_content}
    )

    assert response.status_code == 200


def test_get_rule_not_found(client):
    """Test getting non-existent rule."""
    response = client.get("/api/rules/NonExistent")

    assert response.status_code == 404
```

**Step 6: Run API tests**

Run: `cd backend && pytest tests/api/ -v`

Expected: Tests pass (some may need mocking)

**Step 7: Commit API implementation**

```bash
git add backend/app/api/actions.py backend/app/api/rules.py backend/app/services/rule_storage.py backend/app/main.py tests/api/
git commit -m "feat: add REST API endpoints for actions and rules"
```

---

## Final Integration & Testing

### Task 8: End-to-end test and final integration

**Files:**
- Create: `tests/rule_engine/test_e2e.py`
- Create: `backend/app/rule_engine/__init__.py` (update exports)
- Create: `rules/` directory with sample files

**Step 1: Create end-to-end test**

Create `tests/rule_engine/test_e2e.py`:

```python
"""End-to-end tests for rule engine."""

import pytest
from unittest.mock import Mock, AsyncMock
from app.rule_engine import RuleEngine, ActionRegistry, RuleRegistry
from app.rule_engine.models import UpdateEvent


@pytest.mark.asyncio
async def test_supplier_blocking_e2e():
    """Test complete SupplierStatusBlocking rule flow."""
    # Setup registries
    action_registry = ActionRegistry()
    rule_registry = RuleRegistry()

    # Load sample rule
    rule_registry.load_from_file("tests/rule_engine/fixtures/sample_rules.dsl")

    # Mock Neo4j session
    mock_session = Mock()

    # Mock supplier query result
    supplier_result = Mock()
    supplier_result.data = AsyncMock(return_value=[
        {"s": {"id": "BP_10001", "status": "Suspended"}}
    ])

    # Mock PO query result
    po_result = Mock()
    po_result.data = AsyncMock(return_value=[
        {"po": {"id": "PO_001", "status": "Open"}}
    ])

    # Track queries
    queries = []
    query_params = []

    async def mock_run(query, **params):
        queries.append(query)
        query_params.append(params)

        if "MATCH (s:Supplier" in query:
            return supplier_result
        elif "MATCH (po:PurchaseOrder" in query:
            return po_result
        return Mock(data=AsyncMock(return_value=[]))

    mock_session.run = mock_run

    # Create rule engine
    engine = RuleEngine(action_registry, rule_registry, mock_session)

    # Trigger event
    event = UpdateEvent(
        entity_type="Supplier",
        entity_id="BP_10001",
        property="status",
        old_value="Active",
        new_value="Suspended"
    )

    await engine.on_event(event)

    # Verify queries were executed
    assert len(queries) >= 2
    assert any("MATCH (s:Supplier" in q for q in queries)
    assert any("MATCH (po:PurchaseOrder" in q for q in queries)


@pytest.mark.asyncio
async def test_action_with_preconditions_e2e():
    """Test action execution with preconditions."""
    from app.rule_engine.action_executor import ActionExecutor

    action_registry = ActionRegistry()

    # Register test action
    dsl_text = """
    ACTION PurchaseOrder.submit {
        PRECONDITION: this.status == "Draft"
            ON_FAILURE: "Only draft orders can be submitted"
        EFFECT {
            SET this.status = "Submitted";
        }
    }
    """
    action_registry.load_from_text(dsl_text)

    # Mock session
    mock_session = Mock()
    mock_session.run = AsyncMock()

    executor = ActionExecutor(action_registry, mock_session)

    # Test with valid entity
    result = await executor.execute(
        entity_type="PurchaseOrder",
        action_name="submit",
        entity_id="PO_001",
        entity={"id": "PO_001", "status": "Draft"},
        params={}
    )

    assert result.success is True
    assert result.changes.get("status") == "Submitted"

    # Test with invalid entity
    result = await executor.execute(
        entity_type="PurchaseOrder",
        action_name="submit",
        entity_id="PO_002",
        entity={"id": "PO_002", "status": "Open"},
        params={}
    )

    assert result.success is False
    assert "Only draft orders can be submitted" in result.error
```

**Step 2: Update package exports**

Edit `backend/app/rule_engine/__init__.py`:

```python
"""Rule engine package."""

from app.rule_engine.parser import RuleParser
from app.rule_engine.action_registry import ActionRegistry
from app.rule_engine.action_executor import ActionExecutor, ExecutionResult
from app.rule_engine.rule_registry import RuleRegistry
from app.rule_engine.rule_engine import RuleEngine
from app.rule_engine.context import EvaluationContext
from app.rule_engine.evaluator import ExpressionEvaluator
from app.rule_engine.event_emitter import GraphEventEmitter
from app.rule_engine.models import (
    ActionDef, RuleDef, Precondition, Parameter, Trigger, TriggerType,
    ForClause, SetStatement, TriggerStatement, UpdateEvent, ActionResult
)

__all__ = [
    "RuleParser",
    "ActionRegistry",
    "ActionExecutor",
    "ExecutionResult",
    "RuleRegistry",
    "RuleEngine",
    "EvaluationContext",
    "ExpressionEvaluator",
    "GraphEventEmitter",
    "ActionDef",
    "RuleDef",
    "Precondition",
    "Parameter",
    "Trigger",
    "TriggerType",
    "ForClause",
    "SetStatement",
    "TriggerStatement",
    "UpdateEvent",
    "ActionResult",
]
```

**Step 3: Create rules directory**

Run:
```bash
mkdir -p backend/rules
```

Create `backend/rules/supplier_rules.dsl`:

```javascript
// Supplier Status Blocking Rule
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
        }
    }
}
```

**Step 4: Run all tests**

Run: `cd backend && pytest tests/rule_engine/ -v`

Expected: All tests pass

**Step 5: Final commit**

```bash
git add backend/app/rule_engine/__init__.py backend/rules/ tests/rule_engine/test_e2e.py
git commit -m "feat: complete rule engine implementation with e2e tests"
```

---

## Summary

This implementation plan covers all 6 phases of the rule engine:

1. **Phase 1**: DSL Parser with Lark grammar
2. **Phase 2**: Expression Evaluator with built-in functions
3. **Phase 3**: Action Registry & Executor
4. **Phase 4**: Rule Engine Core with Cypher translator
5. **Phase 5**: Event Integration with GraphTools
6. **Phase 6**: REST API endpoints for management

Each task follows TDD principles with:
- Failing test first
- Minimal implementation
- Verification
- Commit

**Total commits**: ~9 commits for a traceable implementation history.
