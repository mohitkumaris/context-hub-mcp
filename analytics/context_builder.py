"""
Analytics Context Builder for MCP.

Builds structured analytics context for LLM prompts by fetching
current and previous period snapshots from the database.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import desc

from db.session import SessionLocal
from db.models.analytics_snapshot import AnalyticsSnapshot

logger = logging.getLogger(__name__)


class AnalyticsContextBuilder:
    """
    Builds structured analytics context for LLM prompts.
    
    Fetches analytics snapshots from the database and returns
    a strictly structured dictionary with current and previous
    period data for comparison.
    """

    def __init__(self) -> None:
        """Initialize the analytics context builder."""
        logger.info("AnalyticsContextBuilder initialized")

    def _get_session(self):
        """Create a new database session."""
        return SessionLocal()

    def build_analytics_context(
        self,
        channel_uuid: Optional[UUID]
    ) -> dict[str, Any]:
        """
        Build structured analytics context for a channel.
        
        Fetches the two most recent analytics snapshots to provide
        current and previous period data for comparison.
        
        Args:
            channel_uuid: The UUID of the channel to fetch analytics for.
            
        Returns:
            Dictionary with current_period and previous_period data,
            or empty dict if no analytics available.
            
        Example return value:
            {
              "current_period": {
                "period": "last_7_days",
                "views": 45000,
                "subscribers_gained": 320,
                "engagement_rate": 8.5,
                "avg_watch_time_minutes": 4.2
              },
              "previous_period": {
                "period": "previous_7_days",
                "views": 38000,
                "subscribers_gained": 210,
                "engagement_rate": 7.9,
                "avg_watch_time_minutes": 3.9
              }
            }
        """
        if not channel_uuid:
            logger.debug("No channel_uuid provided, returning empty context")
            return {}
        
        try:
            snapshots = self._fetch_recent_snapshots(channel_uuid, limit=2)
            
            if not snapshots:
                logger.debug(f"No analytics snapshots found for channel {channel_uuid}")
                return {}
            
            return self._build_context_dict(snapshots)
            
        except Exception as e:
            logger.error(f"Error building analytics context: {e}")
            return {}

    def _fetch_recent_snapshots(
        self,
        channel_uuid: UUID,
        limit: int = 2
    ) -> list[AnalyticsSnapshot]:
        """
        Fetch the most recent analytics snapshots for a channel.
        
        Args:
            channel_uuid: The UUID of the channel.
            limit: Maximum number of snapshots to fetch (default: 2).
            
        Returns:
            List of AnalyticsSnapshot objects ordered by created_at descending.
        """
        session = self._get_session()
        try:
            snapshots = (
                session.query(AnalyticsSnapshot)
                .filter(AnalyticsSnapshot.channel_id == channel_uuid)
                .order_by(desc(AnalyticsSnapshot.created_at))
                .limit(limit)
                .all()
            )
            return snapshots
        except Exception as e:
            logger.error(f"Error fetching analytics snapshots: {e}")
            raise
        finally:
            session.close()

    def _build_context_dict(
        self,
        snapshots: list[AnalyticsSnapshot]
    ) -> dict[str, Any]:
        """
        Build the structured context dictionary from snapshots.
        
        Args:
            snapshots: List of AnalyticsSnapshot objects (most recent first).
            
        Returns:
            Dictionary with current_period and optionally previous_period.
        """
        context: dict[str, Any] = {}
        
        # Current period (most recent snapshot)
        if len(snapshots) >= 1:
            current = snapshots[0]
            context["current_period"] = self._snapshot_to_dict(
                current, period_label="last_7_days"
            )
        
        # Previous period (second most recent snapshot)
        if len(snapshots) >= 2:
            previous = snapshots[1]
            context["previous_period"] = self._snapshot_to_dict(
                previous, period_label="previous_7_days"
            )
        logger.warning(f"Analytics context resolved: {context}")
        return context

    def _snapshot_to_dict(
        self,
        snapshot: AnalyticsSnapshot,
        period_label: str
    ) -> dict[str, Any]:
        """
        Convert an AnalyticsSnapshot to a structured dictionary.
        
        Args:
            snapshot: The AnalyticsSnapshot object.
            period_label: Label for the period (e.g., "last_7_days").
            
        Returns:
            Dictionary with analytics metrics.
        """
        return {
            "period": snapshot.period or period_label,
            "views": snapshot.views or 0,
            "subscribers_gained": snapshot.subscribers or 0,
            "engagement_rate": snapshot.avg_ctr or 0.0,
            "avg_watch_time_minutes": snapshot.avg_watch_time_minutes or 0.0
        }


# Global instance for convenience
analytics_context_builder = AnalyticsContextBuilder()
