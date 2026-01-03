"""
Policy engine for plan-based access control.

Enforces subscription-based restrictions on tool access.
Plans: free, pro, agency
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlanLimits:
    """Limits for a subscription plan."""

    name: str
    tool_access: set[str]
    daily_requests: int
    max_context_length: int
    deep_analysis_enabled: bool
    priority_support: bool


class PolicyEngine:
    """
    Enforces plan-based access control for tool execution.

    Determines whether a user can execute a specific tool based on
    their subscription plan. Also provides rate limiting info and
    feature flags.
    """

    # Plan hierarchy for comparison
    PLAN_HIERARCHY = ["free", "pro", "agency"]

    # Tool requirements - minimum plan needed for each tool
    TOOL_REQUIREMENTS: dict[str, str] = {
        # Free tier tools
        "fetch_analytics": "free",
        "summarize_data": "free",
        "recall_context": "free",
        "search_data": "free",

        # Pro tier tools
        "compute_metrics": "pro",
        "generate_chart": "pro",
        "analyze_data": "pro",
        "generate_insight": "pro",
        "generate_report": "pro",
        "search_history": "pro",

        # Agency tier tools
        "get_recommendations": "agency",
        "execute_action": "agency",
        "schedule_task": "agency"
    }

    # Plan definitions
    PLANS: dict[str, PlanLimits] = {
        "free": PlanLimits(
            name="free",
            tool_access={"fetch_analytics", "summarize_data",
                         "recall_context", "search_data"},
            daily_requests=50,
            max_context_length=4000,
            deep_analysis_enabled=False,
            priority_support=False
        ),
        "pro": PlanLimits(
            name="pro",
            tool_access={
                "fetch_analytics", "summarize_data", "recall_context", "search_data",
                "compute_metrics", "generate_chart", "analyze_data", "generate_insight",
                "generate_report", "search_history"
            },
            daily_requests=500,
            max_context_length=16000,
            deep_analysis_enabled=True,
            priority_support=False
        ),
        "agency": PlanLimits(
            name="agency",
            tool_access={
                "fetch_analytics", "summarize_data", "recall_context", "search_data",
                "compute_metrics", "generate_chart", "analyze_data", "generate_insight",
                "generate_report", "search_history",
                "get_recommendations", "execute_action", "schedule_task"
            },
            daily_requests=5000,
            max_context_length=32000,
            deep_analysis_enabled=True,
            priority_support=True
        )
    }

    def __init__(self) -> None:
        """Initialize the policy engine."""
        pass

    def can_execute(self, tool_name: str, user_plan: str) -> bool:
        """
        Check if a tool can be executed under a user's plan.

        Args:
            tool_name: Name of the tool to check
            user_plan: User's subscription plan

        Returns:
            True if execution is allowed
        """
        # Get the required plan for this tool
        required_plan = self.TOOL_REQUIREMENTS.get(tool_name)

        if required_plan is None:
            # Unknown tool - deny by default
            logger.warning(f"Unknown tool in policy check: {tool_name}")
            return False

        # Check if user's plan meets the requirement
        return self._plan_meets_requirement(user_plan, required_plan)

    def _plan_meets_requirement(self, user_plan: str, required_plan: str) -> bool:
        """
        Check if user's plan meets or exceeds the required plan.

        Args:
            user_plan: User's current plan
            required_plan: Minimum required plan

        Returns:
            True if user_plan >= required_plan in hierarchy
        """
        try:
            user_level = self.PLAN_HIERARCHY.index(user_plan.lower())
            required_level = self.PLAN_HIERARCHY.index(required_plan.lower())
            return user_level >= required_level
        except ValueError:
            # Unknown plan - assume free
            logger.warning(f"Unknown plan: {user_plan}")
            return required_plan == "free"

    def get_plan_limits(self, user_plan: str) -> PlanLimits:
        """
        Get the limits for a subscription plan.

        Args:
            user_plan: Plan name

        Returns:
            PlanLimits for the plan (defaults to free if unknown)
        """
        return self.PLANS.get(user_plan.lower(), self.PLANS["free"])

    def get_available_tools(self, user_plan: str) -> list[str]:
        """
        Get list of tools available to a plan.

        Args:
            user_plan: Plan name

        Returns:
            List of tool names accessible under this plan
        """
        limits = self.get_plan_limits(user_plan)
        return sorted(list(limits.tool_access))

    def get_blocked_tools(self, user_plan: str) -> list[str]:
        """
        Get list of tools blocked for a plan.

        Args:
            user_plan: Plan name

        Returns:
            List of tool names NOT accessible under this plan
        """
        limits = self.get_plan_limits(user_plan)
        all_tools = set(self.TOOL_REQUIREMENTS.keys())
        blocked = all_tools - limits.tool_access
        return sorted(list(blocked))

    def get_upgrade_suggestion(self, tool_name: str, user_plan: str) -> Optional[str]:
        """
        Get a suggestion for which plan to upgrade to for a tool.

        Args:
            tool_name: Tool that was blocked
            user_plan: Current user plan

        Returns:
            Name of the plan needed, or None if already has access
        """
        if self.can_execute(tool_name, user_plan):
            return None

        required_plan = self.TOOL_REQUIREMENTS.get(tool_name, "agency")
        return required_plan

    def check_rate_limit(self, user_plan: str, current_usage: int) -> tuple[bool, int]:
        """
        Check if user has exceeded their daily rate limit.

        Args:
            user_plan: User's plan
            current_usage: Number of requests made today

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        limits = self.get_plan_limits(user_plan)
        remaining = limits.daily_requests - current_usage

        return (remaining > 0, max(0, remaining))

    def validate_context_length(self, user_plan: str, context_length: int) -> bool:
        """
        Check if context length is within plan limits.

        Args:
            user_plan: User's plan
            context_length: Length of context in characters

        Returns:
            True if within limits
        """
        limits = self.get_plan_limits(user_plan)
        return context_length <= limits.max_context_length

    def can_use_deep_analysis(self, user_plan: str) -> bool:
        """
        Check if deep analysis is available for a plan.

        Args:
            user_plan: User's plan

        Returns:
            True if deep analysis is enabled
        """
        limits = self.get_plan_limits(user_plan)
        return limits.deep_analysis_enabled
