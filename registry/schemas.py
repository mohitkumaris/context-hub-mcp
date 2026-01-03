"""
Pydantic schemas for MCP server.

Defines all request/response models and tool input/output schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ExecuteRequest(BaseModel):
    """
    Request schema for the /execute endpoint.

    Contains all information needed to process a user's context request.
    """

    user_id: str = Field(
        ...,
        description="Unique identifier for the user making the request",
        min_length=1,
        max_length=128,
        examples=["user_abc123"]
    )

    channel_id: str = Field(
        ...,
        description="Channel/conversation context identifier",
        min_length=1,
        max_length=128,
        examples=["channel_xyz789"]
    )

    message: str = Field(
        ...,
        description="User's input message to process",
        min_length=1,
        max_length=10000,
        examples=["Show me the performance metrics for last week"]
    )

    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional additional context for the request",
        examples=[{"user_plan": "pro", "timezone": "UTC"}]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_abc123",
                "channel_id": "channel_xyz789",
                "message": "Give me insights on my channel's growth this month",
                "metadata": {"user_plan": "pro"}
            }
        }


class ExecuteResponse(BaseModel):
    """
    Response schema for the /execute endpoint.

    Contains the processed result along with execution metadata.
    """

    success: bool = Field(
        ...,
        description="Whether the execution completed successfully"
    )

    content: str = Field(
        ...,
        description="Main response content for the user"
    )

    content_type: str = Field(
        default="text",
        description="Type of content: text, analytics, insight, report, error"
    )

    tools_used: list[str] = Field(
        default_factory=list,
        description="List of tool names that were executed"
    )

    tool_outputs: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured outputs from tool executions"
    )

    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Execution metadata including timing and planning info"
    )

    error: Optional[str] = Field(
        default=None,
        description="Error message if execution partially or fully failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "content": "Your channel grew by 15% this month...",
                "content_type": "insight",
                "tools_used": ["fetch_analytics", "generate_insight"],
                "tool_outputs": {
                    "data": {"growth": 15.2, "subscribers": 1250},
                    "insights": ["Strong growth in engagement"]
                },
                "metadata": {
                    "intent": "insight",
                    "confidence": 0.92
                }
            }
        }


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str = Field(
        ...,
        description="Server health status"
    )

    version: str = Field(
        ...,
        description="API version"
    )

    llm_provider: str = Field(
        ...,
        description="Configured LLM provider"
    )


# =============================================================================
# Tool Input/Output Schemas
# =============================================================================

class ToolInputBase(BaseModel):
    """Base schema for tool inputs."""

    message: str = Field(
        ...,
        description="Original user message"
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Memory context for the tool"
    )


class AnalyticsInput(ToolInputBase):
    """Input schema for analytics-related tools."""

    time_range: Optional[str] = Field(
        default="7d",
        description="Time range for data: 1d, 7d, 30d, 90d, 1y"
    )

    metrics: Optional[list[str]] = Field(
        default=None,
        description="Specific metrics to fetch"
    )


class AnalyticsOutput(BaseModel):
    """Output schema for analytics tools."""

    data: dict[str, Any] = Field(
        ...,
        description="Raw analytics data"
    )

    period: str = Field(
        ...,
        description="Time period covered"
    )

    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Computed metrics"
    )


class InsightInput(ToolInputBase):
    """Input schema for insight generation tools."""

    data_source: Optional[str] = Field(
        default=None,
        description="Specific data source to analyze"
    )

    focus_area: Optional[str] = Field(
        default=None,
        description="Area to focus insights on"
    )


class InsightOutput(BaseModel):
    """Output schema for insight tools."""

    insights: list[str] = Field(
        ...,
        description="Generated insights"
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations"
    )

    confidence: float = Field(
        default=0.0,
        description="Confidence score for insights"
    )


class ReportInput(ToolInputBase):
    """Input schema for report generation tools."""

    report_type: str = Field(
        default="summary",
        description="Type of report: summary, detailed, executive"
    )

    time_range: str = Field(
        default="7d",
        description="Time range for report"
    )

    include_charts: bool = Field(
        default=False,
        description="Whether to include chart data"
    )


class ReportOutput(BaseModel):
    """Output schema for report tools."""

    title: str = Field(
        ...,
        description="Report title"
    )

    summary: str = Field(
        ...,
        description="Executive summary"
    )

    sections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Report sections"
    )

    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Report generation timestamp"
    )


class MemoryInput(ToolInputBase):
    """Input schema for memory/context tools."""

    lookup_type: str = Field(
        default="conversation",
        description="Type of memory lookup: conversation, historical, search"
    )

    query: Optional[str] = Field(
        default=None,
        description="Search query for memory lookup"
    )

    limit: int = Field(
        default=10,
        description="Maximum number of results"
    )


class MemoryOutput(BaseModel):
    """Output schema for memory tools."""

    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Memory lookup results"
    )

    total_count: int = Field(
        default=0,
        description="Total available results"
    )

    has_more: bool = Field(
        default=False,
        description="Whether more results are available"
    )


class ActionInput(ToolInputBase):
    """Input schema for action execution tools."""

    action_type: str = Field(
        ...,
        description="Type of action to execute"
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action parameters"
    )

    confirm: bool = Field(
        default=False,
        description="Whether action was confirmed by user"
    )


class ActionOutput(BaseModel):
    """Output schema for action tools."""

    executed: bool = Field(
        ...,
        description="Whether action was executed"
    )

    result: Optional[Any] = Field(
        default=None,
        description="Action result if executed"
    )

    message: str = Field(
        ...,
        description="Human-readable result message"
    )
