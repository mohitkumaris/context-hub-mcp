"""
YouTube Analytics Data Normalizer.

Converts raw YouTube Analytics API responses into snapshot-compatible format.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_analytics_response(raw_response: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize raw YouTube Analytics API response to snapshot format.
    
    Converts the raw API response (with daily rows) into an aggregated
    snapshot format compatible with AnalyticsSnapshot model.
    
    Args:
        raw_response: Raw response from YouTube Analytics API.
        
    Returns:
        Normalized dictionary with aggregated metrics:
        {
            "period": "last_7_days",
            "views": int,
            "subscribers": int,
            "avg_ctr": float,  # Set to 0.0 (CTR not in selected metrics)
            "avg_watch_time_minutes": float
        }
        
        Returns empty dict if no data available.
        
    Note:
        - Sums views and subscribers across all days
        - Calculates average watch time as total_minutes / total_views
        - avg_ctr is set to 0.0 as CTR requires impressions data
    """
    rows = raw_response.get("rows", [])
    column_headers = raw_response.get("columnHeaders", [])
    
    if not rows:
        logger.warning("No analytics rows found in response, returning empty dict")
        return {}
    
    # Build column name to index mapping
    column_map = {
        header["name"]: idx 
        for idx, header in enumerate(column_headers)
    }
    
    logger.debug(f"Column headers: {list(column_map.keys())}")
    
    # Sum values across all days
    total_views = 0
    total_watch_minutes = 0.0
    total_subscribers_gained = 0
    
    for row in rows:
        # Extract values using column indices
        views_idx = column_map.get("views")
        watch_idx = column_map.get("estimatedMinutesWatched")
        subs_idx = column_map.get("subscribersGained")
        
        if views_idx is not None:
            total_views += int(row[views_idx])
        if watch_idx is not None:
            total_watch_minutes += float(row[watch_idx])
        if subs_idx is not None:
            total_subscribers_gained += int(row[subs_idx])
    
    # Calculate average watch time (protect against division by zero)
    if total_views > 0:
        avg_watch_time_minutes = total_watch_minutes / total_views
    else:
        avg_watch_time_minutes = 0.0
        logger.warning("Total views is 0, setting avg_watch_time_minutes to 0.0")
    
    normalized = {
        "period": "last_7_days",
        "views": total_views,
        "subscribers": total_subscribers_gained,
        "avg_ctr": 0.0,  # CTR requires impressions data, not available in current metrics
        "avg_watch_time_minutes": round(avg_watch_time_minutes, 2)
    }
    
    logger.info(
        f"Normalized analytics: views={total_views}, "
        f"subscribers={total_subscribers_gained}, "
        f"avg_watch_time={avg_watch_time_minutes:.2f} min"
    )
    
    return normalized
