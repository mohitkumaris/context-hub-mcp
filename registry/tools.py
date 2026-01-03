"""
MCP Tool Registry.

Registers all available tools with their definitions, schemas,
and stub implementations. Each tool has:
- name: Unique identifier
- description: Human-readable description
- input_schema: Expected input format
- output_schema: Expected output format
- handler: Async function that executes the tool
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_name: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[Any]]
    category: str = "general"
    requires_plan: str = "free"  # Minimum plan required


class ToolRegistry:
    """
    Central registry for all MCP tools.

    Manages tool registration, discovery, and execution.
    Tools are registered at initialization with their schemas
    and handler functions.
    """

    def __init__(self) -> None:
        """Initialize the registry and register all tools."""
        self._tools: dict[str, ToolDefinition] = {}
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        """Register all available MCP tools."""

        # Analytics Tools
        self._register_tool(ToolDefinition(
            name="fetch_analytics",
            description="Fetch analytics data for a channel or time period",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "time_range": {"type": "string", "default": "7d"},
                    "metrics": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                    "period": {"type": "string"},
                    "metrics": {"type": "object"}
                }
            },
            handler=self._fetch_analytics_handler,
            category="analytics",
            requires_plan="free"
        ))

        self._register_tool(ToolDefinition(
            name="compute_metrics",
            description="Compute derived metrics from raw analytics data",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "data": {"type": "object"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "growth_rate": {"type": "number"},
                    "engagement_rate": {"type": "number"},
                    "trends": {"type": "array"}
                }
            },
            handler=self._compute_metrics_handler,
            category="analytics",
            requires_plan="pro"
        ))

        self._register_tool(ToolDefinition(
            name="generate_chart",
            description="Generate chart data for visualization",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "chart_type": {"type": "string", "enum": ["line", "bar", "pie"]},
                    "data": {"type": "object"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string"},
                    "labels": {"type": "array"},
                    "datasets": {"type": "array"}
                }
            },
            handler=self._generate_chart_handler,
            category="analytics",
            requires_plan="pro"
        ))

        # Insight Tools
        self._register_tool(ToolDefinition(
            name="analyze_data",
            description="Perform deep analysis on channel data",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "data_source": {"type": "string"},
                    "focus_area": {"type": "string"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "analysis": {"type": "string"},
                    "key_findings": {"type": "array"},
                    "confidence": {"type": "number"}
                }
            },
            handler=self._analyze_data_handler,
            category="insight",
            requires_plan="pro"
        ))

        self._register_tool(ToolDefinition(
            name="generate_insight",
            description="Generate actionable insights from analyzed data",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "analysis_results": {"type": "object"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "insights": {"type": "array"},
                    "priority": {"type": "string"},
                    "action_items": {"type": "array"}
                }
            },
            handler=self._generate_insight_handler,
            category="insight",
            requires_plan="pro"
        ))

        self._register_tool(ToolDefinition(
            name="get_recommendations",
            description="Get personalized recommendations based on data",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "goal": {"type": "string"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "recommendations": {"type": "array"},
                    "rationale": {"type": "string"},
                    "expected_impact": {"type": "string"}
                }
            },
            handler=self._get_recommendations_handler,
            category="insight",
            requires_plan="agency"
        ))

        # Report Tools
        self._register_tool(ToolDefinition(
            name="generate_report",
            description="Generate a comprehensive report",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "report_type": {"type": "string"},
                    "time_range": {"type": "string"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "sections": {"type": "array"},
                    "generated_at": {"type": "string"}
                }
            },
            handler=self._generate_report_handler,
            category="report",
            requires_plan="pro"
        ))

        self._register_tool(ToolDefinition(
            name="summarize_data",
            description="Create a concise summary of data",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "data": {"type": "object"},
                    "max_length": {"type": "integer"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "highlights": {"type": "array"},
                    "word_count": {"type": "integer"}
                }
            },
            handler=self._summarize_data_handler,
            category="report",
            requires_plan="free"
        ))

        # Memory Tools
        self._register_tool(ToolDefinition(
            name="recall_context",
            description="Recall relevant context from conversation history",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "lookup_type": {"type": "string"},
                    "limit": {"type": "integer"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "has_more": {"type": "boolean"}
                }
            },
            handler=self._recall_context_handler,
            category="memory",
            requires_plan="free"
        ))

        self._register_tool(ToolDefinition(
            name="search_history",
            description="Search through historical data and conversations",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "query": {"type": "string"},
                    "filters": {"type": "object"}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "total_count": {"type": "integer"},
                    "relevance_scores": {"type": "array"}
                }
            },
            handler=self._search_history_handler,
            category="memory",
            requires_plan="pro"
        ))

        # Action Tools
        self._register_tool(ToolDefinition(
            name="execute_action",
            description="Execute a specific action on behalf of the user",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "action_type": {"type": "string"},
                    "parameters": {"type": "object"}
                },
                "required": ["message", "context", "action_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "executed": {"type": "boolean"},
                    "result": {},
                    "message": {"type": "string"}
                }
            },
            handler=self._execute_action_handler,
            category="action",
            requires_plan="agency"
        ))

        self._register_tool(ToolDefinition(
            name="schedule_task",
            description="Schedule a task for future execution",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "task_type": {"type": "string"},
                    "schedule": {"type": "string"},
                    "parameters": {"type": "object"}
                },
                "required": ["message", "context", "task_type"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "scheduled": {"type": "boolean"},
                    "task_id": {"type": "string"},
                    "next_run": {"type": "string"}
                }
            },
            handler=self._schedule_task_handler,
            category="action",
            requires_plan="agency"
        ))

        # Search Tools
        self._register_tool(ToolDefinition(
            name="search_data",
            description="Search across all available data sources",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "context": {"type": "object"},
                    "query": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["message", "context"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "array"},
                    "sources_searched": {"type": "array"},
                    "total_matches": {"type": "integer"}
                }
            },
            handler=self._search_data_handler,
            category="search",
            requires_plan="free"
        ))

    def _register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def list_tools(self) -> list[str]:
        """Return list of all registered tool names."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def get_tools_by_category(self, category: str) -> list[ToolDefinition]:
        """Get all tools in a specific category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_tool_schema(self, name: str) -> Optional[dict[str, Any]]:
        """Get the combined input/output schema for a tool."""
        tool = self.get_tool(name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "input": tool.input_schema,
            "output": tool.output_schema,
            "category": tool.category,
            "requires_plan": tool.requires_plan
        }

    async def execute_tool(
        self,
        tool_name: str,
        input_data: dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            input_data: Input data matching the tool's input schema

        Returns:
            ToolResult with success status and output
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}"
            )

        try:
            output = await tool.handler(input_data)
            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=output
            )
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e)
            )

    # =========================================================================
    # Stub Handler Implementations
    # =========================================================================

    async def _fetch_analytics_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Fetch analytics data."""
        # TODO: Implement actual analytics fetching
        return {
            "data": {
                "views": 15420,
                "subscribers": 1250,
                "engagement": 8.5,
                "watch_time": 45000
            },
            "period": "7d",
            "metrics": {
                "avg_views_per_day": 2203,
                "subscriber_growth": 3.2
            }
        }

    async def _compute_metrics_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Compute derived metrics."""
        # TODO: Implement actual metric computation
        return {
            "growth_rate": 15.2,
            "engagement_rate": 8.5,
            "trends": ["increasing_views", "stable_subscribers"]
        }

    async def _generate_chart_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Generate chart data."""
        # TODO: Implement actual chart generation
        return {
            "chart_type": "line",
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "datasets": [
                {
                    "label": "Views",
                    "data": [1200, 1900, 1500, 2100, 2400, 2200, 2100]
                }
            ]
        }

    async def _analyze_data_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Analyze data."""
        # TODO: Implement actual data analysis
        return {
            "analysis": "Channel shows strong growth trajectory",
            "key_findings": [
                "Peak engagement on weekends",
                "Strong audience retention",
                "Growing subscriber base"
            ],
            "confidence": 0.85
        }

    async def _generate_insight_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Generate insights."""
        # TODO: Implement actual insight generation
        return {
            "insights": [
                "Your weekend content performs 40% better",
                "Shorts are driving subscriber growth",
                "Engagement peaks at 7 PM local time"
            ],
            "priority": "high",
            "action_items": [
                "Post more content on weekends",
                "Increase shorts production",
                "Schedule posts for evening"
            ]
        }

    async def _get_recommendations_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Get recommendations."""
        # TODO: Implement actual recommendation engine
        return {
            "recommendations": [
                "Create a series format for your top-performing topic",
                "Collaborate with channels in similar niche",
                "Optimize thumbnails for mobile viewing"
            ],
            "rationale": "Based on your growth patterns and audience behavior",
            "expected_impact": "15-25% increase in engagement"
        }

    async def _generate_report_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Generate report."""
        # TODO: Implement actual report generation
        from datetime import datetime

        return {
            "title": "Weekly Performance Report",
            "summary": "Strong week with 15% growth in views",
            "sections": [
                {"name": "Overview", "content": "Key metrics summary"},
                {"name": "Engagement", "content": "Audience interaction analysis"},
                {"name": "Growth", "content": "Subscriber and view trends"}
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

    async def _summarize_data_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Summarize data."""
        # TODO: Implement actual summarization
        return {
            "summary": "Your channel had a strong week with 15K views and 50 new subscribers.",
            "highlights": [
                "15,420 total views",
                "50 new subscribers",
                "8.5% engagement rate"
            ],
            "word_count": 15
        }

    async def _recall_context_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Recall context from memory."""
        # TODO: Implement actual context recall
        context = input_data.get("context", {})
        history = context.get("conversation_history", [])

        return {
            "results": history[-5:] if history else [],
            "total_count": len(history),
            "has_more": len(history) > 5
        }

    async def _search_history_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Search history."""
        # TODO: Implement actual history search
        return {
            "results": [
                {"type": "conversation", "content": "Previous discussion about growth"},
                {"type": "insight", "content": "Generated insight from last week"}
            ],
            "total_count": 2,
            "relevance_scores": [0.95, 0.82]
        }

    async def _execute_action_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Execute action."""
        # TODO: Implement actual action execution
        action_type = input_data.get("action_type", "unknown")

        return {
            "executed": False,
            "result": None,
            "message": f"Action '{action_type}' requires user confirmation (stub implementation)"
        }

    async def _schedule_task_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Schedule task."""
        # TODO: Implement actual task scheduling
        import uuid
        from datetime import datetime, timedelta

        return {
            "scheduled": True,
            "task_id": str(uuid.uuid4()),
            "next_run": (datetime.utcnow() + timedelta(days=1)).isoformat()
        }

    async def _search_data_handler(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Stub: Search data."""
        # TODO: Implement actual data search
        return {
            "results": [
                {"source": "analytics", "match": "Performance data"},
                {"source": "history", "match": "Previous conversation"}
            ],
            "sources_searched": ["analytics", "history", "insights"],
            "total_matches": 2
        }
