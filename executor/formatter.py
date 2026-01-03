"""
Response formatter for MCP outputs.

Converts raw tool outputs and LLM responses into clean,
UI-friendly structured responses with metadata.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from executor.planner import ExecutionPlan
from registry.tools import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class FormattedOutput:
    """Structured output ready for API response."""

    content: str
    content_type: str = "text"
    tools_used: list[str] = None  # type: ignore
    tool_outputs: dict[str, Any] = None  # type: ignore
    metadata: dict[str, Any] = None  # type: ignore

    def __post_init__(self) -> None:
        self.tools_used = self.tools_used or []
        self.tool_outputs = self.tool_outputs or {}
        self.metadata = self.metadata or {}


class ResponseFormatter:
    """
    Formats raw outputs into clean, structured API responses.

    Handles:
    - Tool output aggregation
    - Response structure normalization
    - Metadata enrichment
    - Error formatting
    """

    def __init__(self) -> None:
        """Initialize the formatter."""
        self._formatters: dict[str, callable] = {
            "analytics": self._format_analytics,
            "insight": self._format_insight,
            "report": self._format_report,
            "error": self._format_error,
            "general": self._format_general
        }

    def format_response(
        self,
        llm_response: str,
        tool_results: list[ToolResult],
        plan: ExecutionPlan,
        metadata: Optional[dict[str, Any]] = None
    ) -> "ExecuteResponse":
        """
        Format the complete response for API output.

        Args:
            llm_response: Raw LLM response text
            tool_results: Results from tool execution
            plan: The execution plan that was followed
            metadata: Additional request metadata

        Returns:
            ExecuteResponse ready for API
        """
        from registry.schemas import ExecuteResponse

        metadata = metadata or {}

        # Aggregate tool outputs
        tool_outputs = self._aggregate_tool_outputs(tool_results)

        # Get list of tools that were actually used
        tools_used = [r.tool_name for r in tool_results if r.success]

        # Check for any tool errors
        tool_errors = [r for r in tool_results if not r.success]

        # Format the main content
        formatted = self._format_content(
            llm_response=llm_response,
            tool_outputs=tool_outputs,
            intent=plan.intent_classification
        )

        # Build response metadata
        response_metadata = self._build_metadata(
            plan=plan,
            tool_results=tool_results,
            request_metadata=metadata
        )

        # Determine success status
        success = len(tool_errors) == 0 or len(tools_used) > 0

        return ExecuteResponse(
            success=success,
            content=formatted.content,
            content_type=formatted.content_type,
            tools_used=tools_used,
            tool_outputs=formatted.tool_outputs,
            metadata=response_metadata,
            error=self._format_errors(tool_errors) if tool_errors else None
        )

    def _aggregate_tool_outputs(
        self,
        tool_results: list[ToolResult]
    ) -> dict[str, Any]:
        """
        Aggregate outputs from multiple tools.

        Args:
            tool_results: List of tool execution results

        Returns:
            Dictionary mapping tool names to their outputs
        """
        outputs = {}
        for result in tool_results:
            if result.success and result.output is not None:
                outputs[result.tool_name] = result.output

        return outputs

    def _format_content(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any],
        intent: str
    ) -> FormattedOutput:
        """
        Format content based on intent type.

        Args:
            llm_response: Raw LLM response
            tool_outputs: Aggregated tool outputs
            intent: Classified intent type

        Returns:
            FormattedOutput with structured content
        """
        formatter = self._formatters.get(intent, self._formatters["general"])
        return formatter(llm_response, tool_outputs)

    def _format_analytics(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any]
    ) -> FormattedOutput:
        """Format analytics-type responses."""
        # Extract any numeric data from tool outputs
        analytics_data = tool_outputs.get("fetch_analytics", {})
        metrics = tool_outputs.get("compute_metrics", {})

        return FormattedOutput(
            content=llm_response,
            content_type="analytics",
            tool_outputs={
                "data": analytics_data,
                "metrics": metrics,
                "charts": tool_outputs.get("generate_chart")
            }
        )

    def _format_insight(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any]
    ) -> FormattedOutput:
        """Format insight-type responses."""
        insights = tool_outputs.get("generate_insight", [])
        recommendations = tool_outputs.get("get_recommendations", [])

        return FormattedOutput(
            content=llm_response,
            content_type="insight",
            tool_outputs={
                "insights": insights,
                "recommendations": recommendations,
                "analysis": tool_outputs.get("analyze_data")
            }
        )

    def _format_report(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any]
    ) -> FormattedOutput:
        """Format report-type responses."""
        report_data = tool_outputs.get("generate_report", {})
        summary = tool_outputs.get("summarize_data", "")

        return FormattedOutput(
            content=llm_response,
            content_type="report",
            tool_outputs={
                "report": report_data,
                "summary": summary,
                "analytics": tool_outputs.get("fetch_analytics")
            }
        )

    def _format_error(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any]
    ) -> FormattedOutput:
        """Format error responses."""
        return FormattedOutput(
            content=llm_response,
            content_type="error",
            tool_outputs={}
        )

    def _format_general(
        self,
        llm_response: str,
        tool_outputs: dict[str, Any]
    ) -> FormattedOutput:
        """Format general/default responses."""
        return FormattedOutput(
            content=llm_response,
            content_type="text",
            tool_outputs=tool_outputs
        )

    def _build_metadata(
        self,
        plan: ExecutionPlan,
        tool_results: list[ToolResult],
        request_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build comprehensive response metadata.

        Args:
            plan: Execution plan
            tool_results: Tool execution results
            request_metadata: Original request metadata

        Returns:
            Metadata dictionary
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": plan.intent_classification,
            "confidence": plan.confidence,
            "deep_analysis": plan.requires_deep_analysis,
            "planning": {
                "tools_planned": plan.tools_to_execute,
                "tools_executed": len(tool_results),
                "tools_succeeded": len([r for r in tool_results if r.success]),
                "reasoning": plan.reasoning
            },
            "context": {
                "requirements": plan.context_requirements,
                "user_plan": request_metadata.get("user_plan", "free")
            }
        }

    def _format_errors(self, errors: list[ToolResult]) -> str:
        """
        Format tool errors into a readable string.

        Args:
            errors: List of failed tool results

        Returns:
            Formatted error message
        """
        if not errors:
            return ""

        error_messages = []
        for error in errors:
            error_messages.append(f"{error.tool_name}: {error.error}")

        return "; ".join(error_messages)
