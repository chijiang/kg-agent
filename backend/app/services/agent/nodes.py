"""LangGraph node implementations for the enhanced agent."""

import logging
from typing import Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from app.services.agent.state import AgentState, UserIntent
from app.services.agent.prompts import (
    QUERY_SYSTEM_PROMPT,
    ACTION_SYSTEM_PROMPT,
    INTENT_CLASSIFICATION_PROMPT,
)

logger = logging.getLogger(__name__)


class AgentNodes:
    """Collection of LangGraph node functions.

    Each node is an async function that takes the current state
    and returns an updated state.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        query_tools: list[BaseTool],
        action_tools: list | None = None,
    ):
        """Initialize agent nodes.

        Args:
            llm: The LLM instance for decision making and responses
            query_tools: List of query tools for knowledge graph queries
            action_tools: List of action tools for executing operations
        """
        self.llm = llm
        self.query_tools = query_tools
        self.action_tools = action_tools or []

        # Bind tools to LLM for query operations
        self.query_llm_with_tools = llm.bind_tools(query_tools)

        # Create prompts
        self.query_prompt = ChatPromptTemplate.from_messages([
            ("system", QUERY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])

        self.action_prompt = ChatPromptTemplate.from_messages([
            ("system", ACTION_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
        ])

        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_CLASSIFICATION_PROMPT),
            ("human", "{input}"),
        ])

    async def router_node(self, state: AgentState) -> AgentState:
        """Determine the user's intent and route to appropriate handler.

        This node classifies the user's message into:
        - QUERY: Information seeking, needs query tools
        - ACTION: Wants to perform operations, needs action tools
        - DIRECT_ANSWER: General conversation, no tools needed

        Args:
            state: Current agent state

        Returns:
            Updated state with classified intent
        """
        last_message = state["messages"][-1]

        # Get user input
        if hasattr(last_message, "content"):
            user_input = last_message.content
        else:
            user_input = str(last_message)

        logger.info(f"Router processing: {user_input[:100]}...")

        # Simple keyword-based intent classification
        # More sophisticated LLM-based classification can be added
        user_input_lower = user_input.lower()

        # Action keywords (Chinese and English)
        action_keywords = [
            "执行", "运行", "操作", "处理", "付款", "支付", "提交", "批准", "删除", "更新", "修改",
            "execute", "run", "perform", "pay", "submit", "approve", "delete", "update", "modify"
        ]

        # Query keywords
        query_keywords = [
            "查找", "搜索", "显示", "展示", "列出", "有多少", "什么是", "哪个", "查询",
            "find", "search", "show", "list", "how many", "what is", "which", "query"
        ]

        # Check for action intent
        if any(keyword in user_input_lower for keyword in action_keywords):
            intent = UserIntent.ACTION
        # Check for query intent
        elif any(keyword in user_input_lower for keyword in query_keywords):
            intent = UserIntent.QUERY
        # Default to query
        else:
            intent = UserIntent.QUERY

        logger.info(f"Classified intent as: {intent}")

        state["user_intent"] = intent
        state["current_step"] = "routed"

        return state

    async def query_tools_node(self, state: AgentState) -> AgentState:
        """Execute query tools to gather information.

        This node uses tool calling with the LLM to execute
        the appropriate query tools based on the user's question.

        Args:
            state: Current agent state

        Returns:
            Updated state with query results
        """
        logger.info("Executing query tools node")

        # Prepare messages with system prompt
        messages_with_prompt = await self.query_prompt.ainvoke({"messages": state["messages"]})

        # Get response with tool calls
        response = await self.query_llm_with_tools.ainvoke(messages_with_prompt)

        # Add the response to state
        state["messages"].append(response)

        # If there are tool calls, execute them
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = []

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                # Find and execute the tool
                tool = next((t for t in self.query_tools if t.name == tool_name), None)
                if tool:
                    try:
                        result = await tool.ainvoke(tool_args)
                        tool_messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_id,
                            name=tool_name
                        ))
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        tool_messages.append(ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_id,
                            name=tool_name
                        ))

            # Add tool messages to state
            state["messages"].extend(tool_messages)

            # Get final response from LLM
            final_response = await self.llm.ainvoke(state["messages"] + tool_messages)
            state["messages"].append(final_response)

        state["current_step"] = "queried"

        return state

    async def action_tools_node(self, state: AgentState) -> AgentState:
        """Plan and prepare action execution.

        This node identifies targets and plans action execution.
        Actual execution happens in batch_executor_node (Phase 2).

        Args:
            state: Current agent state

        Returns:
            Updated state with action plan
        """
        logger.info("Executing action tools node")

        # For now, use query tools to identify targets
        # Full action execution will be implemented in Phase 2

        # Prepare messages with system prompt
        messages_with_prompt = await self.action_prompt.ainvoke({"messages": state["messages"]})

        # Get response
        response = await self.query_llm_with_tools.ainvoke(messages_with_prompt)
        state["messages"].append(response)

        # If there are tool calls, execute them
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_messages = []

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                tool = next((t for t in self.query_tools if t.name == tool_name), None)
                if tool:
                    try:
                        result = await tool.ainvoke(tool_args)
                        tool_messages.append(ToolMessage(
                            content=str(result),
                            tool_call_id=tool_id,
                            name=tool_name
                        ))
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        tool_messages.append(ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_id,
                            name=tool_name
                        ))

            state["messages"].extend(tool_messages)

            # Get final response
            final_response = await self.llm.ainvoke(state["messages"] + tool_messages)
            state["messages"].append(final_response)

        state["current_step"] = "action_planned"

        return state

    async def answer_node(self, state: AgentState) -> AgentState:
        """Generate a direct answer without tools.

        This node handles general conversation and direct answers.

        Args:
            state: Current agent state

        Returns:
            Updated state with AI response
        """
        logger.info("Executing answer node")

        last_message = state["messages"][-1]

        if hasattr(last_message, "content"):
            user_input = last_message.content
        else:
            user_input = str(last_message)

        # Simple response for direct answer
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个知识图谱助手。简洁友好地回应用户。"),
            ("human", "{input}")
        ])

        chain = prompt | self.llm

        try:
            result = await chain.ainvoke({"input": user_input})
            ai_message = AIMessage(content=result.content)
        except Exception as e:
            logger.error(f"Error in answer_node: {e}")
            ai_message = AIMessage(content="抱歉，我现在无法处理您的请求。")

        state["messages"].append(ai_message)
        state["current_step"] = "answered"

        return state

    async def summary_node(self, state: AgentState) -> AgentState:
        """Summarize action execution results.

        This node creates a summary of batch action execution.

        Args:
            state: Current agent state

        Returns:
            Updated state with summary
        """
        logger.info("Executing summary node")

        # Will be fully implemented in Phase 2 when action execution is ready
        summary = "Action 执行汇总功能将在 Phase 2 中实现。"
        ai_message = AIMessage(content=summary)
        state["messages"].append(ai_message)

        return state


def route_decision(state: AgentState) -> Literal["query_tools", "action_tools", "answer"]:
    """Decide which node to route to based on user intent.

    Args:
        state: Current agent state

    Returns:
        Name of the next node to execute
    """
    intent = state.get("user_intent", UserIntent.QUERY)

    if intent == UserIntent.QUERY:
        return "query_tools"
    elif intent == UserIntent.ACTION:
        return "action_tools"
    else:
        return "answer"
