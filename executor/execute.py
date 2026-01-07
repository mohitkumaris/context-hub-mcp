"""
Main orchestration entry point for MCP request execution.

This module coordinates:
- Memory loading (short-term and long-term)
- Tool planning and execution
- LLM invocation
- Response formatting
- Persistence of chat history and insights

All business logic flows through here.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from config import config
from executor.planner import ExecutionPlanner, ExecutionPlan
from executor.formatter import ResponseFormatter
from registry.tools import ToolRegistry, ToolResult
from registry.schemas import ExecuteResponse
from registry.policies import PolicyEngine
from memory.redis_store import RedisMemoryStore
from memory.postgres_store import PostgresMemoryStore
from db.models.analytics_snapshot import AnalyticsSnapshot
from db.models.weekly_insight import WeeklyInsight
from db.models.chat_session import ChatSession

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

        # Convert string IDs to UUIDs for database operations
        user_uuid = self._safe_parse_uuid(user_id)
        channel_uuid = self._safe_parse_uuid(channel_id)

        # Step 1: Load memory context (short-term + long-term)
        logger.debug(
            f"Loading memory for user={user_id}, channel={channel_id}")
        memory_context = await self._load_memory_context(user_id, channel_id)

        # Step 1b: Load historical context from PostgreSQL
        historical_context = self._load_historical_context(
            channel_uuid, user_uuid)
        memory_context["historical"] = historical_context

        # Step 2: Plan tool execution (with historical context)
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
            tool_results = await self._execute_tools(
                approved_tools, message, memory_context
            )

        # Step 5: Call LLM with full context (including historical)
        logger.debug("Calling LLM")
        llm_response = await self._call_llm(
            message=message,
            memory_context=memory_context,
            tool_results=tool_results,
            plan=plan
        )

        # Step 6: Store conversation in short-term memory (Redis)
        await self._store_conversation(
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            response=llm_response,
            tools_used=[t.tool_name for t in tool_results]
        )

        # Step 7: Persist to long-term memory (PostgreSQL) - non-blocking
        self._persist_to_postgres(
            user_uuid=user_uuid,
            channel_uuid=channel_uuid,
            message=message,
            response=llm_response,
            tool_results=tool_results,
            confidence=plan.confidence if hasattr(plan, "confidence") else None
        )

        # Step 8: Format and return response
        return self.formatter.format_response(
            llm_response=llm_response,
            tool_results=tool_results,
            plan=plan,
            metadata=metadata
        )

    def _safe_parse_uuid(self, id_str: str) -> Optional[UUID]:
        """
        Safely parse a string to UUID.

        Args:
            id_str: String representation of UUID

        Returns:
            UUID object or None if invalid
        """
        try:
            return UUID(id_str)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {id_str}")
            return None

    def _load_historical_context(
        self,
        channel_uuid: Optional[UUID],
        user_uuid: Optional[UUID]
    ) -> dict[str, Any]:
        """
        Load historical context from PostgreSQL long-term memory.

        Args:
            channel_uuid: Channel UUID for analytics and insights
            user_uuid: User UUID for chat history

        Returns:
            Dictionary containing historical context
        """
        historical_context: dict[str, Any] = {
            "latest_snapshot": None,
            "recent_insights": [],
            "recent_chats": []
        }

        # Load latest analytics snapshot for channel
        if channel_uuid:
            try:
                snapshot = self.postgres_store.get_latest_analytics_snapshot(
                    channel_uuid
                )
                if snapshot:
                    historical_context["latest_snapshot"] = {
                        "period": snapshot.period,
                        "subscribers": snapshot.subscribers,
                        "views": snapshot.views,
                        "avg_ctr": snapshot.avg_ctr,
                        "avg_watch_time_minutes": snapshot.avg_watch_time_minutes,
                        "created_at": snapshot.created_at.isoformat()
                        if snapshot.created_at else None
                    }
            except Exception as e:
                logger.error(f"Failed to load analytics snapshot: {e}")

            # Load recent weekly insights (limit 3)
            try:
                insights = self.postgres_store.get_recent_weekly_insights(
                    channel_uuid, limit=3
                )
                historical_context["recent_insights"] = [
                    {
                        "week_start": insight.week_start.isoformat()
                        if insight.week_start else None,
                        "summary": insight.summary,
                        "wins": insight.wins,
                        "losses": insight.losses,
                        "next_actions": insight.next_actions
                    }
                    for insight in insights
                ]
            except Exception as e:
                logger.error(f"Failed to load weekly insights: {e}")

        # Load recent chat sessions for user (limit 5)
        if user_uuid:
            try:
                chats = self.postgres_store.get_recent_chat_sessions(
                    user_uuid, channel_id=channel_uuid, limit=5
                )
                historical_context["recent_chats"] = [
                    {
                        "user_message": chat.user_message,
                        "assistant_response": chat.assistant_response,
                        "tools_used": chat.tools_used,
                        "created_at": chat.created_at.isoformat()
                        if chat.created_at else None
                    }
                    for chat in chats
                ]
            except Exception as e:
                logger.error(f"Failed to load chat sessions: {e}")

        return historical_context

    def _persist_to_postgres(
        self,
        user_uuid: Optional[UUID],
        channel_uuid: Optional[UUID],
        message: str,
        response: str,
        tool_results: list[ToolResult],
        confidence: Optional[float] = None
    ) -> None:
        """
        Persist execution results to PostgreSQL long-term memory.

        This method handles:
        - Chat session persistence
        - Conditional analytics snapshot persistence
        - Conditional weekly insight persistence

        Args:
            user_uuid: User UUID
            channel_uuid: Channel UUID
            message: User's message
            response: Assistant's response
            tool_results: Results from tool execution
            confidence: Confidence score of the response
        """
        # Persist chat session (requires valid user_uuid)
        if user_uuid:
            try:
                tools_used_list = [
                    t.tool_name for t in tool_results if t.success]
                chat_session = ChatSession(
                    user_id=user_uuid,
                    channel_id=channel_uuid,
                    user_message=message,
                    assistant_response=response,
                    tools_used={
                        "tools": tools_used_list} if tools_used_list else None,
                    confidence=confidence
                )
                self.postgres_store.save_chat_session(chat_session)
                logger.debug("Chat session persisted to PostgreSQL")
            except Exception as e:
                # Non-blocking: log error but don't fail the request
                logger.error(f"Failed to persist chat session: {e}")
        else:
            logger.warning(
                "Skipping chat session persistence: invalid user_id")

        # Conditional persistence based on tool outputs
        if channel_uuid:
            self._persist_tool_outputs(channel_uuid, tool_results)

    def _persist_tool_outputs(
        self,
        channel_uuid: UUID,
        tool_results: list[ToolResult]
    ) -> None:
        """
        Conditionally persist analytics and insights from tool outputs.

        Args:
            channel_uuid: Channel UUID
            tool_results: Results from tool execution
        """
        for result in tool_results:
            if not result.success or not result.output:
                continue

            output = result.output

            # Check for analytics snapshot data
            if self._is_analytics_snapshot_output(result.tool_name, output):
                try:
                    snapshot = AnalyticsSnapshot(
                        channel_id=channel_uuid,
                        period=output.get("period", "unknown"),
                        subscribers=output.get("subscribers", 0),
                        views=output.get("views", 0),
                        avg_ctr=output.get("avg_ctr", 0.0),
                        avg_watch_time_minutes=output.get(
                            "avg_watch_time_minutes", 0.0
                        )
                    )
                    self.postgres_store.save_analytics_snapshot(snapshot)
                    logger.debug(
                        f"Analytics snapshot persisted from {result.tool_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to persist analytics snapshot: {e}")

            # Check for weekly insight data
            if self._is_weekly_insight_output(result.tool_name, output):
                try:
                    from datetime import date as date_type
                    week_start = output.get("week_start")
                    if isinstance(week_start, str):
                        week_start = date_type.fromisoformat(week_start)

                    insight = WeeklyInsight(
                        channel_id=channel_uuid,
                        week_start=week_start or date_type.today(),
                        summary=output.get("summary"),
                        wins=output.get("wins"),
                        losses=output.get("losses"),
                        next_actions=output.get("next_actions")
                    )
                    self.postgres_store.save_weekly_insight(insight)
                    logger.debug(
                        f"Weekly insight persisted from {result.tool_name}"
                    )
                except Exception as e:
                    logger.error(f"Failed to persist weekly insight: {e}")

    def _is_analytics_snapshot_output(
        self, tool_name: str, output: Any
    ) -> bool:
        """
        Check if tool output contains analytics snapshot data.

        Args:
            tool_name: Name of the executed tool
            output: Tool output data

        Returns:
            True if output contains analytics snapshot data
        """
        analytics_tools = {
            "fetch_analytics",
            "get_channel_snapshot",
            "compute_metrics"
        }

        if tool_name in analytics_tools and isinstance(output, dict):
            # Check for required analytics fields
            return any(
                key in output
                for key in ["subscribers", "views", "avg_ctr"]
            )
        return False

    def _is_weekly_insight_output(self, tool_name: str, output: Any) -> bool:
        """
        Check if tool output contains weekly insight data.

        Args:
            tool_name: Name of the executed tool
            output: Tool output data

        Returns:
            True if output contains weekly insight data
        """
        insight_tools = {
            "weekly_growth_report",
            "generate_insight",
            "analyze_data"
        }

        if tool_name in insight_tools and isinstance(output, dict):
            # Check for weekly insight structure
            return any(
                key in output
                for key in ["summary", "wins", "losses", "next_actions"]
            )
        return False

    async def _load_memory_context(
        self,
        user_id: str,
        channel_id: str
    ) -> dict[str, Any]:
        """
        Load relevant context from short-term memory (Redis).

        Long-term context is loaded separately via _load_historical_context.

        Args:
            user_id: User identifier
            channel_id: Channel identifier

        Returns:
            Memory context dictionary with short-term data
        """
        # Load short-term context (recent conversation from Redis)
        short_term = await self.redis_store.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id
        )

        return {
            "conversation_history": short_term.get("messages", []),
            "session_state": short_term.get("state", {}),
            # Historical context is added in execute() via _load_historical_context
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
            memory_context: Loaded memory context (including historical)
            tool_results: Results from tool execution
            plan: Execution plan for context

        Returns:
            LLM-generated response string
        """
        # Load system prompt
        system_prompt = self._load_prompt("system")

        # Build context for LLM
        context_parts = []

        # Add conversation history (short-term from Redis)
        history = memory_context.get("conversation_history", [])
        if history:
            context_parts.append("Recent conversation:")
            for msg in history[-5:]:  # Last 5 messages
                context_parts.append(
                    f"- {msg.get('role', 'user')}: {msg.get('content', '')}")

        # Add historical context from PostgreSQL
        historical = memory_context.get("historical", {})

        # Add latest analytics snapshot
        latest_snapshot = historical.get("latest_snapshot")
        if latest_snapshot:
            context_parts.append("\nLatest channel analytics:")
            context_parts.append(
                f"- Period: {latest_snapshot.get('period')}"
            )
            context_parts.append(
                f"- Subscribers: {latest_snapshot.get('subscribers'):,}"
            )
            context_parts.append(
                f"- Views: {latest_snapshot.get('views'):,}"
            )
            context_parts.append(
                f"- Avg CTR: {latest_snapshot.get('avg_ctr', 0):.2f}%"
            )
            context_parts.append(
                f"- Avg Watch Time: {latest_snapshot.get('avg_watch_time_minutes', 0):.1f} min"
            )

        # Add recent weekly insights
        recent_insights = historical.get("recent_insights", [])
        if recent_insights:
            context_parts.append("\nRecent weekly insights:")
            for insight in recent_insights:
                if insight.get("summary"):
                    context_parts.append(
                        f"- Week {insight.get('week_start')}: {insight.get('summary')}"
                    )
                if insight.get("wins"):
                    wins = insight['wins']
                    wins_str = ', '.join(wins) if isinstance(
                        wins, list) else str(wins)
                    context_parts.append(f"  Wins: {wins_str}")

        # Add recent chat history from PostgreSQL
        recent_chats = historical.get("recent_chats", [])
        if recent_chats:
            context_parts.append("\nPrevious conversations:")
            for chat in recent_chats[:3]:  # Limit to 3 for context
                user_msg = chat.get("user_message", "")[:100]  # Truncate
                context_parts.append(f"- User: {user_msg}...")

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
        Store the conversation turn in short-term memory (Redis).

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
