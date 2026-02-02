# Rule Engine Implementation Design

**Date**: 2025-02-03
**Status**: Approved
**Approach**: One working example first (SupplierStatusBlocking rule)

---

## Overview

Complete implementation of a rule engine system supporting ACTION definitions with PRECONDITIONs and RULE definitions for reactive state management over a Neo4j knowledge graph.

### Scope

All 6 phases of implementation:
1. DSL Parser
2. Expression Evaluator
3. Action Registry & Executor
4. Rule Engine Core
5. Event Integration
6. API & Management

### Primary Example

**Rule 1: SupplierStatusBlocking** - Lock POs/PRs when supplier status changes to Suspended/Blacklisted/Expired.

```javascript
RULE SupplierStatusBlocking PRIORITY 100 {
    ON UPDATE(Supplier.status)
    FOR (s: Supplier WHERE s.status IN ["Expired", "Blacklisted", "Suspended"]) {
        FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open") {
            SET po.status = "RiskLocked";
        }
        FOR (pr: PurchaseRequisition
             WHERE EXISTS(po: PurchaseOrder
                         WHERE po -[createdFrom]-> pr AND po -[orderedFrom]-> s)
             AND pr.status == "Open") {
            SET pr.status = "RiskLocked";
        }
    }
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  /api/graph │  │ /api/actions│  │   /api/rules│         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Rule Engine Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │DSL Parser   │  │Action       │  │Rule Engine  │         │
│  │(Lark)       │  │Registry     │  │Core         │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Existing Services                        │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │GraphTools   │  │Neo4j Pool   │                           │
│  │(modified)   │  │             │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: DSL Parser

**Dependencies**: `lark >= 1.1`

### Files
| File | Purpose |
|------|---------|
| `grammar.lark` | Lark grammar for ACTION/RULE syntax |
| `ast_nodes.py` | Dataclasses for AST nodes |
| `parser.py` | Parser class with `parse()` method |

### Key AST Nodes
```python
@dataclass
class RuleDef:
    name: str
    priority: int
    trigger: Trigger
    body: ForClause

@dataclass
class ForClause:
    variable: str
    entity_type: str
    condition: Expression | None
    statements: list[Statement]

@dataclass
class SetStatement:
    target: Path
    value: Expression
```

### API
```python
from app.rule_engine import RuleParser

parser = RuleParser()
ast = parser.parse(dsl_text)
# Returns: list[ActionDef | RuleDef]
```

---

## Phase 2: Expression Evaluator

### Files
| File | Purpose |
|------|---------|
| `context.py` | EvaluationContext class |
| `evaluator.py` | ExpressionEvaluator class |
| `functions.py` | Built-in functions (NOW, CONCAT, OLD, etc.) |

### API
```python
from app.rule_engine import ExpressionEvaluator, EvaluationContext

ctx = EvaluationContext(
    entity={"id": "BP_10001", "status": "Suspended"},
    old_values={"status": "Active"},
    session=neo4j_session
)
evaluator = ExpressionEvaluator(ctx)
result = evaluator.evaluate(ast_expression)
```

---

## Phase 3: Action Registry & Executor

### Files
| File | Purpose |
|------|---------|
| `action_registry.py` | ActionRegistry class |
| `action_executor.py` | ActionExecutor class |
| `effect_handlers.py` | SET, CREATE, LINK, TRIGGER handlers |
| `graph_mutator.py` | Neo4j write operations |

### API
```python
from app.rule_engine import ActionRegistry, ActionExecutor

registry = ActionRegistry()
registry.load_from_file("rules/actions.dsl")

executor = ActionExecutor(registry, neo4j_session)
result = await executor.execute(
    entity_type="PurchaseOrder",
    action_name="submit",
    entity_id="PO_001",
    params={}
)
```

---

## Phase 4: Rule Engine Core

### Files
| File | Purpose |
|------|---------|
| `rule_registry.py` | RuleRegistry with trigger index |
| `rule_engine.py` | RuleEngine core class |
| `cypher_translator.py` | FOR clause to Cypher query |

### Cypher Translation Example
```
DSL: FOR (po: PurchaseOrder WHERE po -[orderedFrom]-> s AND po.status == "Open")
→ Cypher: MATCH (po:PurchaseOrder)-[:orderedFrom]->(s:Supplier {id: $supplierId})
         WHERE po.status = "Open"
         RETURN po
```

### API
```python
from app.rule_engine import RuleEngine

engine = RuleEngine(action_registry, neo4j_session)
engine.load_rules_from_file("rules/business_rules.dsl")

await engine.on_event(UpdateEvent(
    entity_type="Supplier",
    entity_id="BP_10001",
    property="status",
    old_value="Active",
    new_value="Suspended"
))
```

---

## Phase 5: Event Integration

### Files
| File | Purpose |
|------|---------|
| `event_emitter.py` | GraphEventEmitter class |
| `graph_tools.py` | Modified to emit events |

### Event Flow
```python
async def update_entity(self, entity_id: str, updates: dict):
    old = await self.get_entity(entity_id)
    await self._do_update(entity_id, updates)

    for key, new_val in updates.items():
        if old.get(key) != new_val:
            await self.event_emitter.emit(UpdateEvent(
                entity_type=old["__type__"],
                entity_id=entity_id,
                property=key,
                old_value=old.get(key),
                new_value=new_val
            ))
```

---

## Phase 6: API & Management

### Files
| File | Purpose |
|------|---------|
| `actions.py` | POST `/api/actions/{type}/{action}` |
| `rules.py` | GET/POST/DELETE `/api/rules` |
| `rule_storage.py` | Rule file persistence |

### API Endpoints
```
POST /api/actions/{entity_type}/{action_name}
  Body: { "entity_id": "PO_001", "params": {...} }
  Response: { "success": true } or { "success": false, "error": "..." }

GET  /api/rules
POST /api/rules          # Upload DSL file
GET  /api/rules/{name}
DELETE /api/rules/{name}

GET  /api/actions        # List all registered actions
```

---

## File Structure

```
backend/app/rule_engine/
├── __init__.py
├── grammar.lark
├── ast_nodes.py
├── parser.py
├── context.py
├── evaluator.py
├── functions.py
├── action_registry.py
├── action_executor.py
├── effect_handlers.py
├── graph_mutator.py
├── rule_registry.py
├── rule_engine.py
├── cypher_translator.py
├── event_emitter.py
└── models.py

backend/app/api/
├── actions.py
└── rules.py

backend/app/services/
└── rule_storage.py

tests/rule_engine/
├── fixtures/
│   └── sample_rules.dsl
├── test_parser.py
├── test_evaluator.py
├── test_action_executor.py
├── test_rule_engine.py
├── test_cypher_translator.py
├── test_integration.py
└── test_e2e.py
```

---

## Dependencies

Add to `pyproject.toml`:
```toml
[project.dependencies]
lark = "^1.1"
```

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Cascade loops | High | Max cascade depth limit (10), visited set |
| Cypher injection | High | Parameterized queries only |
| Performance (large graphs) | Medium | Index FOR patterns, batch updates |
| Complex nested patterns | Medium | Limit pattern depth, clear error messages |
