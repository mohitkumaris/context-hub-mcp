"""
Main orchestration entry point for MCP request execution.

This module coordinates:
- Memory loading (short-term and long-term)
- Tool planning and execution
- LLM invocation
- Response formatting

All business logic flows through here.
"""

import logging
from typing import Any, Optional

from config import config
from executor.planner import ExecutionPlanner, ExecutionPlan
from executor.formatter import ResponseFormatter
from registry.tools import ToolRegistry, ToolResult
from registry.schemas import ExecuteResponse
from registry.policies import PolicyEngine
from memory.redis_store import RedisMemoryStore
from memory.postgres_store import PostgresMemoryStore

logger = logging.getLogger(__name__)


class ContextOrchestrator:
    """
    Core orchestrator for MCP context requests.

    Coordinates all components to process a user request:
    1. Load relevant context from memory stores
    2. Plan tool execution based on user intent
    3. Execute approved tools
    4. Call LLM with full context
    5. Format and return response
    """

    def __init__(self) -> None:
        """Initialize orchestrator with all required components."""
        self.planner = ExecutionPlanner()
        self.formatter = ResponseFormatter()
        self.tool_registry = ToolRegistry()
        self.policy_engine = PolicyEngine()
        self.redis_store = RedisMemoryStore()
        self.postgres_store = PostgresMemoryStore()

    async def execute(
        self,
        user_id: str,
        channel_id: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> ExecuteResponse:
        """
        Execute a full context request cycle.

        Args:
            user_id: Unique identifier for the user
            channel_id: Channel/conversation context identifier
            message: User's input message
            metadata: Optional additional context

        Returns:
            ExecuteResponse with result and metadata
        """
        metadata = metadata or {}
        tool_results: list[ToolResult] = []

        # Step 1: Load memory context
        logger.debug(
            f"Loading memory for user={user_id}, channel={channel_id}")
        memory_context = await self._load_memory_context(user_id, channel_id)

        # Step 2: Plan tool execution
        logger.debug("Planning tool execution")
        plan = self.planner.create_plan(
            message=message,
            memory_context=memory_context,
            available_tools=self.tool_registry.list_tools()
        )

        # Step 3: Check policy permissions
        user_plan = metadata.get("user_plan", "free")
        approved_tools = self._filter_by_policy(plan, user_plan)

        # Step 4: Execute approved tools
        if approved_tools:
            logger.debug(f"Executing {len(approved_tools)} tools")
            tool_results = await self._execute_tools(approved_tools, message, memory_context)

        # Step 5: Call LLM with full context
        logger.debug("Calling LLM")
        llm_response = await self._call_llm(
            message=message,
            memory_context=memory_context,
            tool_results=tool_results,
            plan=plan
        )

        # Step 6: Store conversation in memory
        await self._store_conversation(
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            response=llm_response,
            tools_used=[t.tool_name for t in tool_results]
        )

        # Step 7: Format and return response
        return self.formatter.format_response(
            llm_response=llm_response,
            tool_results=tool_results,
            plan=plan,
            metadata=metadata
        )

    async def _load_memory_context(
        self,
        user_id: str,
        channel_id: str
    ) -> dict[str, Any]:
        """
        Load relevant context from both memory stores.

        Args:
            user_id: User identifier
            channel_id: Channel identifier

        Returns:
            Combined memory context dictionary
        """
        # Load short-term context (recent conversation)
        short_term = await self.redis_store.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id
        )

        # Load long-term context (historical data)
        long_term = await self.postgres_store.get_channel_context(
            channel_id=channel_id
        )

        return {
            "conversation_history": short_term.get("messages", []),
            "session_state": short_term.get("state", {}),
            "channel_snapshots": long_term.get("snapshots", []),
            "historical_insights": long_term.get("insights", []),
            "analytics": long_term.get("analytics", {})
        }

    def _filter_by_policy(
        self,
        plan: ExecutionPlan,
        user_plan: str
    ) -> list[str]:
        """
        Filter planned tools by user's subscription plan.

        Args:
            plan: Execution plan from planner
            user_plan: User's subscription tier

        Returns:
            List of tool names approved for execution
        """
        approved = []
        for tool_name in plan.tools_to_execute:
            if self.policy_engine.can_execute(tool_name, user_plan):
                approved.append(tool_name)
            else:
                logger.info(
                    f"Tool {tool_name} blocked by policy for plan {user_plan}")

        return approved

    async def _execute_tools(
        self,
        tool_names: list[str],
        message: str,
        context: dict[str, Any]
    ) -> list[ToolResult]:
        """
        Execute a list of tools and collect results.

        Args:
            tool_names: Names of tools to execute
            message: Original user message
            context: Memory context for tool execution

        Returns:
            List of tool execution results
        """
        results = []
        for tool_name in tool_names:
            try:
                result = await self.tool_registry.execute_tool(
                    tool_name=tool_name,
                    input_data={
                        "message": message,
                        "context": context
                    }
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                results.append(ToolResult(
                    tool_name=tool_name,
                    success=False,
                    output=None,
                    error=str(e)
                ))

        return results

    async def _call_llm(
        self,
        message: str,
        memory_context: dict[str, Any],
        tool_results: list[ToolResult],
        plan: ExecutionPlan
    ) -> str:
        """
        Call the LLM with full context to generate response.

        Args:
            message: User's input message
            memory_context: Loaded memory context
            tool_results: Results from tool execution
            plan: Execution plan for context

        Returns:
            LLM-generated response string
        """
        # Load system prompt
        system_prompt = self._load_prompt("system")

        # Build context for LLM
        context_parts = []

        # Add conversation history
        history = memory_context.get("conversation_history", [])
        if history:
            context_parts.append("Recent conversation:")
            for msg in history[-5:]:  # Last 5 messages
                context_parts.append(
                    f"- {msg.get('role', 'user')}: {msg.get('content', '')}")

        # Add tool results
        if tool_results:
            context_parts.append("\nTool execution results:")
            for result in tool_results:
                if result.success:
                    context_parts.append(
                        f"- {result.tool_name}: {result.output}")
                else:
                    context_parts.append(
                        f"- {result.tool_name}: Error - {result.error}")

        # Add historical insights if available
        insights = memory_context.get("historical_insights", [])
        if insights:
            context_parts.append("\nHistorical insights:")
            for insight in insights[:3]:
                context_parts.append(f"- {insight}")

        full_context = "\n".join(
            context_parts) if context_parts else "No additional context."

        # Build the prompt
        full_prompt = f"""
{system_prompt}

Context:
{full_context}

User message: {message}

Provide a helpful, data-backed response.
"""

        # Call LLM (stub implementation - replace with actual provider)
        response = await self._invoke_llm(full_prompt)

        return response

    async def _invoke_llm(self, prompt: str) -> str:
        """
        Invoke the configured LLM provider.

        This is a stub implementation. In production, this would call
        the actual LLM API based on config.llm.provider.

        Args:
            prompt: Full prompt to send to LLM

        Returns:
            LLM response string
        """
        # Stub implementation - returns a placeholder
        # TODO: Implement actual LLM provider integration
        logger.info(
            f"LLM invocation (stub): provider={config.llm.provider}, model={config.llm.model}")

        return (
            "This is a stub LLM response. In production, this would contain "
            "the actual response from the configured LLM provider "
            f"({config.llm.provider}/{config.llm.model}). "
            "The response would be based on the provided context and tools."
        )

    def _load_prompt(self, prompt_type: str) -> str:
        """
        Load a prompt template from the prompts directory.

        Args:
            prompt_type: Type of prompt ("system" or "analysis")

        Returns:
            Prompt template string
        """
        import os

        prompt_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            f"{prompt_type}.txt"
        )

        try:
            with open(prompt_file, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_file}")
            return ""

    async def _store_conversation(
        self,
        user_id: str,
        channel_id: str,
        message: str,
        response: str,
        tools_used: list[str]
    ) -> None:
        """
        Store the conversation turn in memory.

        Args:
            user_id: User identifier
            channel_id: Channel identifier
            message: User's message
            response: Generated response
            tools_used: List of tools that were executed
        """
        await self.redis_store.store_message(
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            response=response,
            tools_used=tools_used
        )


# Global orchestrator instance
_orchestrator: Optional[ContextOrchestrator] = None


def get_orchestrator() -> ContextOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ContextOrchestrator()
    return _orchestrator


async def execute_context_request(
    user_id: str,
    channel_id: str,
    message: str,
    metadata: Optional[dict[str, Any]] = None
) -> ExecuteResponse:
    """
    Public API for executing a context request.

    This is the main entry point called by the server endpoint.

    Args:
        user_id: Unique identifier for the user
        channel_id: Channel/conversation context identifier
        message: User's input message
        metadata: Optional additional context

    Returns:
        ExecuteResponse with processed result
    """
    orchestrator = get_orchestrator()
    return await orchestrator.execute(
        user_id=user_id,
        channel_id=channel_id,
        message=message,
        metadata=metadata
    )
