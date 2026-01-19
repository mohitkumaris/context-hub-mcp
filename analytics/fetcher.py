"""
YouTube Analytics Data Fetcher.

Fetches analytics data from the YouTube Analytics API for the last 7 days.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from clients.youtube_analytics import YouTubeAnalyticsClient

logger = logging.getLogger(__name__)


class AnalyticsFetcher:
    """
    Fetches YouTube Analytics data for a channel.
    
    Uses the YouTube Analytics API to retrieve metrics for the last 7 days,
    broken down by day.
    """
    
    # Metrics to fetch from YouTube Analytics API
    DEFAULT_METRICS = (
        "views,"
        "estimatedMinutesWatched,"
        "averageViewDuration,"
        "subscribersGained"
    )
    
    def __init__(self, client: YouTubeAnalyticsClient) -> None:
        """
        Initialize the fetcher with a YouTube Analytics client.
        
        Args:
            client: Authenticated YouTubeAnalyticsClient instance.
        """
        self.client = client
        logger.debug("AnalyticsFetcher initialized")
    
    def fetch_last_7_days(self) -> dict[str, Any]:
        """
        Fetch analytics data for the last 7 days.
        
        Retrieves views, watch time, average view duration, and subscribers
        gained for each day in the period.
        
        Returns:
            Raw API response with daily analytics data.
            
        Note:
            The date range excludes today (as data may be incomplete)
            and includes the 7 previous days.
        """
        # Calculate date range (yesterday to 7 days ago)
        today = datetime.utcnow().date()
        end_date = today - timedelta(days=1)  # Yesterday (complete data)
        start_date = today - timedelta(days=7)  # 7 days ago
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        logger.info(
            f"Fetching YouTube Analytics for last 7 days: "
            f"{start_str} to {end_str}"
        )
        
        response = self.client.query_reports(
            start_date=start_str,
            end_date=end_str,
            metrics=self.DEFAULT_METRICS,
            dimensions="day",
            sort="day"
        )
        
        row_count = len(response.get("rows", []))
        logger.info(f"Fetched {row_count} days of analytics data")
        
        return response


def fetch_analytics_for_channel(
    access_token: str,
    refresh_token: str | None = None
) -> dict[str, Any]:
    """
    Convenience function to fetch analytics for a channel.
    
    Creates a client and fetcher, then retrieves the last 7 days of data.
    Supports automatic token refresh if OAuth credentials expire.
    
    Args:
        access_token: OAuth access token for the channel.
        refresh_token: Optional OAuth refresh token for automatic token refresh.
        
    Returns:
        Raw API response with analytics data.
    """
    client = YouTubeAnalyticsClient(
        access_token=access_token,
        refresh_token=refresh_token
    )
    fetcher = AnalyticsFetcher(client)
    return fetcher.fetch_last_7_days()
