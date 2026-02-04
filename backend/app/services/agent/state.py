"""Agent state definitions for LangGraph."""

from typing import Annotated, TypedDict, Required
from typing_extensions import NotRequired
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State for the enhanced QA agent.

    The agent maintains this state through the LangGraph execution,
    updating it as nodes process the user's request.
    """

    # Conversation history - managed by LangGraph
    messages: Annotated[list, add_messages]

    # Intent classification
    user_intent: NotRequired[str]  # "query", "action", "direct_answer"

    # Current execution info for progress tracking
    current_step: NotRequired[str]

    # Query-related state
    query_results: NotRequired[list[dict]]

    # Graph visualization data
    graph_data: NotRequired[dict]

    # Action execution state
    action_plan: NotRequired[dict]
    batch_results: NotRequired[dict]


class ActionPlan(TypedDict):
    """Planned action execution."""

    entity_type: str
    action_name: str
    target_count: int
    targets: list[dict]  # [{"entity_id": str, "entity_name": str}]


class ActionResultSummary(TypedDict):
    """Summary of action execution results."""

    total: int
    succeeded: int
    failed: int
    successes: list[dict]  # [{"entity_id": str, "changes": dict}]
    failures: list[dict]  # [{"entity_id": str, "error": str}]


class StreamEvent(TypedDict, total=False):
    """SSE stream event types."""

    type: Required[str]  # Event type discriminator

    # Thinking/progress events
    content: NotRequired[str]
    conversation_id: NotRequired[int]

    # Graph data for visualization
    nodes: NotRequired[list[dict]]
    edges: NotRequired[list[dict]]

    # Action planning
    plan: NotRequired[ActionPlan]

    # Action progress
    completed: NotRequired[int]
    total: NotRequired[int]
    entity_id: NotRequired[str]
    success: NotRequired[bool]

    # Action results
    results: NotRequired[ActionResultSummary]

    # Action error
    error: NotRequired[str]


class UserIntent:
    """User intent constants."""

    QUERY = "query"
    ACTION = "action"
    DIRECT_ANSWER = "direct_answer"


# Valid intent values
VALID_INTENTS = {UserIntent.QUERY, UserIntent.ACTION, UserIntent.DIRECT_ANSWER}
