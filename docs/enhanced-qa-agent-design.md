# Enhanced QA Agent Design Document

## 1. Overview

### 1.1 Goals

Transform the current `QAAgent` from a simple query-based system into a full-featured agent with two categories of tools:

1. **Query Tools**: Query knowledge graph for information (existing functionality)
2. **Action Tools**: Execute actions on entity instances (new functionality)

### 1.2 Key Requirements

- **Framework**: Use LangGraph for agent orchestration (avoid custom maintenance burden)
- **Concurrency**: Support batch concurrent action execution (e.g., 20 orders paid simultaneously)
- **Transparency**: Report success/failure details back to the user
- **Streaming**: Maintain streaming responses for real-time feedback

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                │
│  - Chat UI with action progress indicators                      │
│  - Real-time streaming updates                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ SSE / HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  /chat/stream Endpoint                                   │  │
│  │  - Streams agent thinking, tool calls, and results       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              EnhancedAgentService (LangGraph)             │  │
│  │                                                           │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │  │
│  │  │   Router    │───▶│ Query Tools │───▶│   Answer     │   │  │
│  │  │   Node      │    │             │    │   Node       │   │  │
│  │  └─────────────┘    └─────────────┘    └──────────────┘   │  │
│  │       │                                                    │  │
│  │       ▼                                                    │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐   │  │
│  │  │   Action    │───▶│   Batch     │───▶│   Summary    │   │  │
│  │  │   Tools     │    │ Executor    │    │   Node       │   │  │
│  │  └─────────────┘    └─────────────┘    └──────────────┘   │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Tool Registry                           │  │
│  │  - QueryToolRegistry (KG queries)                         │  │
│  │  - ActionToolRegistry (Entity actions)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Existing Services                       │  │
│  │  - GraphTools (Neo4j queries)                             │  │
│  │  - ActionExecutor (execute ACTION definitions)            │  │
│  │  - ActionRegistry (lookup actions)                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Neo4j Knowledge Graph                      │
│  - Instance data (PurchaseOrder, Supplier, etc.)               │
│  - Ontology (Class definitions, relationships)                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 LangGraph State Graph

```
                    ┌─────────────┐
                    │    Start    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Router    │◀─────┐
                    └──┬──────┬───┘      │
          ┌───────────┘      │          │
          │                  │          │
          ▼                  ▼          │
    ┌───────────┐      ┌──────────┐    │
    │  Query    │      │  Action  │    │
    │  Tools    │      │  Tools   │    │
    └─────┬─────┘      └────┬─────┘    │
          │                  │          │
          ▼                  ▼          │
    ┌───────────┐      ┌──────────┐    │
    │  Answer   │      │  Batch   │    │
    │  Node     │      │ Executor │    │
    └───────────┘      └────┬─────┘    │
                             │          │
                             ▼          │
                      ┌──────────┐     │
                      │  Summary │─────┘
                      │  Node    │
                      └────┬─────┘
                           │
                           ▼
                    ┌─────────────┐
                    │     End     │
                    └─────────────┘
```

## 3. Tool Design

### 3.1 Query Tools (Existing + Enhanced)

These tools query the knowledge graph for information without making changes.

| Tool Name | Description | Input | Output |
|-----------|-------------|-------|--------|
| `search_instances` | Search for entity instances | search_term, class_name?, limit? | List of matching instances |
| `get_instance_neighbors` | Get related entities | instance_name, hops?, direction? | Neighboring entities and relationships |
| `get_instances_by_class` | Get all instances of a type | class_name, filters?, limit? | List of instances |
| `find_path_between_instances` | Find relationship path | start_name, end_name, max_depth? | Path information |
| `get_ontology_classes` | Get schema class definitions | - | Class definitions |
| `get_ontology_relationships` | Get schema relationships | - | Relationship definitions |
| `describe_class` | Get detailed class info | class_name | Class schema details |
| `get_node_statistics` | Get statistics | node_label? | Count and samples |

### 3.2 Action Tools (New)

These tools execute ACTION definitions on entity instances.

| Tool Name | Description | Input | Output |
|-----------|-------------|-------|--------|
| `list_available_actions` | List actions for an entity type | entity_type | Available actions with preconditions |
| `get_action_details` | Get action details including preconditions | entity_type, action_name | Full action definition |
| `execute_action` | Execute a single action | entity_type, action_name, entity_id, params? | Execution result |
| `batch_execute_action` | Execute action on multiple entities concurrently | entity_type, action_name, entity_ids, params? | Batch results with successes/failures |
| `validate_action_preconditions` | Check if action can execute | entity_type, action_name, entity_id | Validation result with reasons |

## 4. LangGraph Implementation

### 4.1 Agent State

```python
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """State for the enhanced QA agent."""
    # Conversation history
    messages: Annotated[list, add_messages]

    # Current task info
    user_intent: str  # "query" or "action"
    current_step: str  # For progress tracking

    # Query results
    query_results: list[dict]
    graph_data: dict | None  # Nodes and edges for visualization

    # Action execution results
    action_plan: dict | None  # Planned actions
    batch_results: dict | None  # Results of batch execution
```

### 4.2 Graph Structure

```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

class EnhancedAgentService:
    """Enhanced QA Agent using LangGraph."""

    def __init__(self, neo4j_config, action_executor, action_registry):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.action_executor = action_executor
        self.action_registry = action_registry
        self.neo4j_config = neo4j_config

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("query_tools", self._query_tools_node)
        workflow.add_node("action_tools", self._action_tools_node)
        workflow.add_node("batch_executor", self._batch_executor_node)
        workflow.add_node("answer", self._answer_node)
        workflow.add_node("summary", self._summary_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add edges
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "query": "query_tools",
                "action": "action_tools",
                "direct_answer": "answer",
            }
        )
        workflow.add_edge("query_tools", "answer")
        workflow.add_edge("action_tools", "batch_executor")
        workflow.add_edge("batch_executor", "summary")

        workflow.add_edge("answer", END)
        workflow.add_edge("summary", END)

        return workflow.compile()
```

### 4.3 Node Implementations

#### Router Node

```python
async def _router_node(self, state: AgentState) -> AgentState:
    """Determine if the user wants to query or execute actions."""
    last_message = state["messages"][-1].content

    # Use LLM to classify intent
    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", """Classify the user's intent as:
        - QUERY: User wants to search, find, count, or explore data
        - ACTION: User wants to modify, create, delete, or execute operations
        - ANSWER: Direct question that doesn't require tools

        Return only one word: QUERY, ACTION, or ANSWER"""),
        ("human", "{input}")
    ])

    chain = intent_prompt | self.llm
    result = await chain.ainvoke({"input": last_message})
    state["user_intent"] = result.content.strip().upper()

    return state
```

#### Query Tools Node

```python
async def _query_tools_node(self, state: AgentState) -> AgentState:
    """Execute query tools using LangChain's agent executor."""
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.tools import StructuredTool

    # Create query tools
    tools = self._create_query_tools()

    # Create agent
    agent = create_tool_calling_agent(self.llm, tools, prompt=QUERY_PROMPT)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True
    )

    # Execute
    result = await agent_executor.ainvoke({
        "input": state["messages"][-1].content
    })

    state["query_results"] = result.get("intermediate_steps", [])
    return state
```

#### Action Tools Node

```python
async def _action_tools_node(self, state: AgentState) -> AgentState:
    """Plan and prepare action execution."""
    from langchain.agents import AgentExecutor, create_tool_calling_agent

    tools = self._create_action_tools()
    agent = create_tool_calling_agent(self.llm, tools, prompt=ACTION_PROMPT)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    result = await agent_executor.ainvoke({
        "input": state["messages"][-1].content
    })

    # Parse action plan from tool calls
    state["action_plan"] = self._parse_action_plan(result)
    return state
```

#### Batch Executor Node

```python
async def _batch_executor_node(self, state: AgentState) -> AgentState:
    """Execute actions in batch with concurrency."""
    action_plan = state["action_plan"]
    if not action_plan:
        return state

    results = {
        "success": [],
        "failed": [],
        "total": len(action_plan["executions"])
    }

    # Execute concurrently
    tasks = []
    for execution in action_plan["executions"]:
        task = self._execute_single_action(execution)
        tasks.append(task)

    # Wait for all with concurrent limit
    import asyncio
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

    async def bounded_execute(task):
        async with semaphore:
            return await task

    bounded_tasks = [bounded_execute(t) for t in tasks]
    task_results = await asyncio.gather(*bounded_tasks, return_exceptions=True)

    # Collect results
    for i, result in enumerate(task_results):
        execution = action_plan["executions"][i]
        if isinstance(result, Exception):
            results["failed"].append({
                "entity_id": execution["entity_id"],
                "error": str(result)
            })
        elif result.success:
            results["success"].append({
                "entity_id": execution["entity_id"],
                "changes": result.changes
            })
        else:
            results["failed"].append({
                "entity_id": execution["entity_id"],
                "error": result.error
            })

    state["batch_results"] = results
    return state

async def _execute_single_action(self, execution: dict):
    """Execute a single action."""
    from app.rule_engine.context import EvaluationContext

    driver = await get_neo4j_driver(**self.neo4j_config)
    async with driver.session() as session:
        context = EvaluationContext(
            entity={"id": execution["entity_id"]},
            old_values={},
            session=session,
            variables=execution.get("params", {})
        )
        return await self.action_executor.execute(
            execution["entity_type"],
            execution["action_name"],
            context
        )
```

## 5. Batch Concurrency Design

### 5.1 Concurrency Strategy

```python
import asyncio
from dataclasses import dataclass
from typing import Any

@dataclass
class BatchExecutionConfig:
    """Configuration for batch execution."""
    max_concurrent: int = 10  # Max concurrent actions
    timeout_per_action: int = 30  # Seconds
    retry_on_failure: bool = False
    max_retries: int = 1

class BatchActionExecutor:
    """Handles concurrent batch execution of actions."""

    async def execute_batch(
        self,
        executions: list[dict],
        config: BatchExecutionConfig
    ) -> dict:
        """Execute actions concurrently with controlled parallelism.

        Args:
            executions: List of execution specs with entity_type, action_name, entity_id
            config: Concurrency configuration

        Returns:
            Results with success/failed groups
        """
        semaphore = asyncio.Semaphore(config.max_concurrent)

        async def bounded_execution(execution: dict):
            async with semaphore:
                return await self._execute_with_timeout(
                    execution,
                    config.timeout_per_action
                )

        tasks = [bounded_execution(e) for e in executions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._aggregate_results(executions, results)

    async def _execute_with_timeout(self, execution: dict, timeout: int):
        """Execute with timeout protection."""
        try:
            return await asyncio.wait_for(
                self._execute_single(execution),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return ActionResult(
                success=False,
                error=f"Timeout after {timeout}s"
            )
```

### 5.2 Progress Streaming

```python
class StreamingBatchExecutor(BatchActionExecutor):
    """Batch executor with progress streaming."""

    def __init__(self, progress_callback):
        self.progress_callback = progress_callback

    async def execute_batch(self, executions: list[dict], config: BatchExecutionConfig):
        """Execute with progress updates."""
        total = len(executions)
        completed = 0

        async def tracked_execution(execution: dict):
            nonlocal completed
            result = await self._execute_single(execution)
            completed += 1

            # Stream progress
            await self.progress_callback({
                "type": "action_progress",
                "completed": completed,
                "total": total,
                "entity_id": execution["entity_id"],
                "success": result.success
            })

            return result

        # Modify parent class to use tracked_execution
        ...
```

## 6. API Design

### 6.1 Streaming Response Format

The SSE stream will include new event types for action execution:

```typescript
type StreamEvent =
  // Existing
  | { type: "thinking"; content: string; conversation_id?: number }
  | { type: "content"; content: string }
  | { type: "content_start" }
  | { type: "graph_data"; nodes: Node[]; edges: Edge[] }
  | { type: "conversation_id"; id: number }
  | { type: "done" }

  // New - Action related
  | { type: "action_plan"; plan: ActionPlan }  // Planned actions
  | { type: "action_progress"; completed: number; total: number; entity_id: string; success: boolean }
  | { type: "action_complete"; results: ActionResultSummary }
  | { type: "action_error"; entity_id: string; error: string }

interface ActionPlan {
  entity_type: string;
  action_name: string;
  target_count: number;
  targets: { entity_id: string; entity_name: string }[];
}

interface ActionResultSummary {
  total: number;
  succeeded: number;
  failed: number;
  successes: { entity_id: string; changes: Record<string, any> }[];
  failures: { entity_id: string; error: string }[];
}
```

### 6.2 API Endpoint

```python
@router.post("/chat/stream")
async def chat_stream_v2(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enhanced streaming chat with action support."""
    # Initialize agent
    agent_service = EnhancedAgentService(
        neo4j_config=neo4j_dict,
        action_executor=app.state.action_executor,
        action_registry=app.state.action_registry
    )

    async def event_generator():
        full_content = ""
        graph_data = None

        async for event in agent_service.astream_events(req.query):
            # Process different event types
            if event["type"] == "thinking":
                yield _sse_event(event)
            elif event["type"] == "content":
                full_content += event["content"]
                yield _sse_event(event)
            elif event["type"] == "action_plan":
                yield _sse_event(event)
            elif event["type"] == "action_progress":
                yield _sse_event(event)
            elif event["type"] == "action_complete":
                # Save results to DB
                yield _sse_event(event)
            elif event["type"] == "graph_data":
                graph_data = event

        # Save message
        await _save_assistant_message(db, conversation.id, full_content, graph_data)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## 7. Tool Definitions

### 7.1 Query Tools Implementation

```python
# backend/app/services/agent_tools/query_tools.py

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List

class SearchInstancesInput(BaseModel):
    search_term: str = Field(description="Search keyword")
    class_name: Optional[str] = Field(None, description="Entity type to filter")
    limit: int = Field(10, description="Max results")

async def search_instances(
    search_term: str,
    class_name: Optional[str] = None,
    limit: int = 10
) -> str:
    """Search for entity instances in the knowledge graph.

    Use this when user wants to find specific entities by name or ID.
    """
    async with await get_neo4j_session() as session:
        tools = GraphTools(session)
        results = await tools.search_instances(search_term, class_name, limit)
        return _format_results(results)

# Create all query tools
QUERY_TOOLS = [
    StructuredTool.from_function(
        coroutine=search_instances,
        name="search_instances",
        description="Search for entity instances in the knowledge graph",
        args_schema=SearchInstancesInput
    ),
    # ... other query tools
]
```

### 7.2 Action Tools Implementation

```python
# backend/app/services/agent_tools/action_tools.py

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ListAvailableActionsInput(BaseModel):
    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")

async def list_available_actions(entity_type: str) -> str:
    """List all available actions for an entity type.

    Returns action names, parameters, and preconditions.
    """
    actions = action_registry.list_by_entity(entity_type)
    return _format_action_list(actions)

class ExecuteActionInput(BaseModel):
    entity_type: str = Field(description="Entity type, e.g., PurchaseOrder")
    action_name: str = Field(description="Action name, e.g., submit")
    entity_id: str = Field(description="Entity ID")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")

async def execute_action(
    entity_type: str,
    action_name: str,
    entity_id: str,
    params: Dict[str, Any] = None
) -> str:
    """Execute a single action on an entity instance.

    Important: This checks all preconditions before executing.
    """
    context = await _create_context(entity_id, params or {})
    result = await action_executor.execute(entity_type, action_name, context)

    if result.success:
        return f"Action {action_name} executed on {entity_id}. Changes: {result.changes}"
    else:
        return f"Action failed: {result.error}"

class BatchExecuteActionInput(BaseModel):
    entity_type: str = Field(description="Entity type")
    action_name: str = Field(description="Action name")
    entity_ids: List[str] = Field(description="List of entity IDs")
    params: Dict[str, Any] = Field(default_factory=dict, description="Shared parameters")

async def batch_execute_action(
    entity_type: str,
    action_name: str,
    entity_ids: List[str],
    params: Dict[str, Any] = None
) -> str:
    """Execute an action on multiple entities concurrently.

    This is the preferred method for bulk operations.
    Returns summary with success/failure breakdown.
    """
    config = BatchExecutionConfig(max_concurrent=10)
    executions = [
        {"entity_type": entity_type, "action_name": action_name, "entity_id": eid, "params": params}
        for eid in entity_ids
    ]

    results = await batch_executor.execute_batch(executions, config)
    return _format_batch_results(results)

ACTION_TOOLS = [
    StructuredTool.from_function(
        coroutine=list_available_actions,
        name="list_available_actions",
        description="List available actions for an entity type",
        args_schema=ListAvailableActionsInput
    ),
    StructuredTool.from_function(
        coroutine=execute_action,
        name="execute_action",
        description="Execute a single action on an entity instance",
        args_schema=ExecuteActionInput
    ),
    StructuredTool.from_function(
        coroutine=batch_execute_action,
        name="batch_execute_action",
        description="Execute an action on multiple entities concurrently (preferred for bulk)",
        args_schema=BatchExecuteActionInput
    ),
    # ... other action tools
]
```

## 8. Prompt Engineering

### 8.1 System Prompts

```python
QUERY_SYSTEM_PROMPT = """You are a knowledge graph query assistant. You have access to tools that can query the knowledge graph.

When a user asks questions:
1. Use the query tools to find relevant information
2. Synthesize the results into a clear, helpful answer
3. If you find entities, mention their IDs and types
4. If the user might want to take action, suggest available actions

Available tools: search_instances, get_instance_neighbors, get_instances_by_class,
find_path_between_instances, get_ontology_classes, get_ontology_relationships,
describe_class, get_node_statistics"""

ACTION_SYSTEM_PROMPT = """You are a knowledge graph action executor. You can execute actions on entity instances.

Important guidelines:
1. ALWAYS use batch_execute_action for multiple entities (preferred)
2. Use list_available_actions first to understand what actions are available
3. Each action has preconditions that must be met
4. Report success/failure clearly to the user
5. If preconditions fail, explain why

When a user wants to perform actions:
1. Use query tools to identify target entities
2. Use list_available_actions to check available operations
3. Use batch_execute_action for bulk operations
4. Summarize results with clear success/failure breakdown

Available tools: search_instances, get_instances_by_class, list_available_actions,
execute_action, batch_execute_action, validate_action_preconditions"""
```

## 9. File Structure

```
backend/app/services/
├── agent/
│   ├── __init__.py
│   ├── agent_service.py       # Main LangGraph agent service
│   ├── state.py               # Agent state definitions
│   ├── nodes.py               # LangGraph node implementations
│   ├── graph.py               # LangGraph construction
│   └── prompts.py             # System prompts
│
├── agent_tools/
│   ├── __init__.py
│   ├── query_tools.py         # Query tool implementations
│   ├── action_tools.py        # Action tool implementations
│   └── tool_registry.py       # Tool registration
│
├── batch_executor.py          # New: Batch concurrent execution
│
├── qa_agent.py                # Existing: Keep for backward compatibility
├── graph_tools.py             # Existing: Query tools
└── schema_matcher.py          # Existing: Schema matching
```

## 10. Implementation Phases

### Phase 1: Foundation
- [ ] Create agent service structure
- [ ] Implement basic LangGraph with router node
- [ ] Migrate existing query tools to LangChain tool format
- [ ] Test query-only flows

### Phase 2: Action Tools
- [ ] Implement list_available_actions tool
- [ ] Implement execute_action tool
- [ ] Implement batch_execute_action tool
- [ ] Add action result formatting

### Phase 3: Batch Execution
- [ ] Implement BatchActionExecutor
- [ ] Add concurrency control with semaphore
- [ ] Implement progress streaming
- [ ] Add timeout and error handling

### Phase 4: Integration
- [ ] Update /chat/stream endpoint
- [ ] Add new SSE event types
- [ ] Update frontend to handle action events
- [ ] End-to-end testing

### Phase 5: Polish
- [ ] Add action execution history tracking
- [ ] Implement undo/rollback capability
- [ ] Add action validation before execution
- [ ] Performance optimization

## 11. Example Conversation Flow

```
User: 把供应商XXX的全部订单进行付款

Agent Events (Stream):
1. thinking: "正在分析请求..."
2. thinking: "识别意图: ACTION - 批量执行"
3. action_plan: {
     "entity_type": "PurchaseOrder",
     "action_name": "makePayment",
     "targets": [PO_001, PO_002, PO_003, ...]
   }
4. action_progress: {"completed": 1, "total": 20, "entity_id": "PO_001", "success": true}
5. action_progress: {"completed": 2, "total": 20, "entity_id": "PO_002", "success": true}
6. action_progress: {"completed": 3, "total": 20, "entity_id": "PO_003", "success": false}
   ... (concurrent execution)
7. action_complete: {
     "total": 20,
     "succeeded": 18,
     "failed": 2,
     "successes": [...],
     "failures": [
       {"entity_id": "PO_003", "error": "Insufficient funds"},
       {"entity_id": "PO_015", "error": "Order already paid"}
     ]
   }
8. content: "已完成对供应商XXX的20个订单的付款处理。
              成功: 18个订单
              失败: 2个订单
              - PO_003: 余额不足
              - PO_015: 订单已付款
              "
```
