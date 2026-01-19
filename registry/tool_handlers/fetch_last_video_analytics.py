"""
fetch_last_video_analytics MCP Tool.

Fetches the most recently published video's analytics data from YouTube,
normalizes it, and returns structured performance metrics.

This is a PRO-only tool that enables detailed video performance analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from registry.base import ToolResult

logger = logging.getLogger(__name__)


class YouTubeVideoFetcher:
    """
    Fetches video data from YouTube Data API and Analytics API.
    
    Uses OAuth credentials to fetch the most recently published video
    and its analytics metrics.
    """
    
    def __init__(self, access_token: str) -> None:
        """
        Initialize the fetcher with OAuth access token.
        
        Args:
            access_token: OAuth access token for authenticated API calls.
        """
        self.access_token = access_token
        self._data_service = None
        self._analytics_service = None
    
    def _get_credentials(self) -> Credentials:
        """Build OAuth credentials from access token."""
        return Credentials(token=self.access_token)
    
    def _get_data_service(self) -> Any:
        """Get or create YouTube Data API service."""
        if self._data_service is None:
            credentials = self._get_credentials()
            self._data_service = build(
                "youtube",
                "v3",
                credentials=credentials,
                cache_discovery=False
            )
        return self._data_service
    
    def _get_analytics_service(self) -> Any:
        """Get or create YouTube Analytics API service."""
        if self._analytics_service is None:
            credentials = self._get_credentials()
            self._analytics_service = build(
                "youtubeAnalytics",
                "v2",
                credentials=credentials,
                cache_discovery=False
            )
        return self._analytics_service
    
    def get_latest_video(self) -> Optional[dict[str, Any]]:
        """
        Fetch the most recently published video for the authenticated channel.
        
        Returns:
            Video details dict or None if no videos found.
        """
        service = self._get_data_service()
        
        # Step 1: Get the channel's uploads playlist ID
        channels_response = service.channels().list(
            part="contentDetails",
            mine=True
        ).execute()
        
        if not channels_response.get("items"):
            logger.warning("No channel found for authenticated user")
            return None
        
        uploads_playlist_id = (
            channels_response["items"][0]
            ["contentDetails"]["relatedPlaylists"]["uploads"]
        )
        
        # Step 2: Get the latest video from uploads playlist
        playlist_response = service.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=1
        ).execute()
        
        if not playlist_response.get("items"):
            logger.warning("No videos found in channel uploads")
            return None
        
        latest_item = playlist_response["items"][0]
        video_id = latest_item["snippet"]["resourceId"]["videoId"]
        
        # Step 3: Get full video details including statistics
        videos_response = service.videos().list(
            part="snippet,statistics",
            id=video_id
        ).execute()
        
        if not videos_response.get("items"):
            logger.warning(f"Could not fetch details for video {video_id}")
            return None
        
        video = videos_response["items"][0]
        snippet = video["snippet"]
        statistics = video.get("statistics", {})
        
        return {
            "video_id": video_id,
            "title": snippet.get("title", "Untitled"),
            "published_at": snippet.get("publishedAt"),
            "views": int(statistics.get("viewCount", 0)),
            "likes": int(statistics.get("likeCount", 0)),
            "comments": int(statistics.get("commentCount", 0))
        }
    
    def get_video_analytics(self, video_id: str) -> dict[str, Any]:
        """
        Fetch analytics metrics for a specific video.
        
        Args:
            video_id: YouTube video ID to fetch analytics for.
            
        Returns:
            Analytics metrics dict.
        """
        service = self._analytics_service
        
        # Calculate date range (from video publish to now, max 28 days back)
        today = datetime.utcnow().date()
        end_date = today - timedelta(days=1)  # Yesterday for complete data
        start_date = today - timedelta(days=28)  # Last 28 days
        
        try:
            # Query video-specific analytics
            # Note: Not all metrics may be available for all videos
            if self._analytics_service is None:
                self._get_analytics_service()
            
            response = self._analytics_service.reports().query(
                ids="channel==MINE",
                startDate=start_date.strftime("%Y-%m-%d"),
                endDate=end_date.strftime("%Y-%m-%d"),
                metrics="views,averageViewDuration,estimatedMinutesWatched",
                filters=f"video=={video_id}"
            ).execute()
            
            rows = response.get("rows", [])
            if rows:
                # Metrics order: views, averageViewDuration, estimatedMinutesWatched
                return {
                    "views": int(rows[0][0]) if len(rows[0]) > 0 else 0,
                    "avg_view_duration_seconds": float(rows[0][1]) if len(rows[0]) > 1 else 0,
                    "watch_time_minutes": float(rows[0][2]) if len(rows[0]) > 2 else 0
                }
            
        except HttpError as e:
            # Analytics might not be available for very new videos
            logger.warning(f"Could not fetch analytics for video {video_id}: {e}")
        
        return {}


async def handle_fetch_last_video_analytics(input_data: dict[str, Any]) -> ToolResult:
    """
    Handle the fetch_last_video_analytics tool execution.
    
    Fetches the most recently published video and its performance analytics
    using YouTube Data API and Analytics API.
    
    Args:
        input_data: Dictionary containing:
            - context: Dict with "channel" key containing OAuth tokens
            
    Returns:
        ToolResult with success status and structured video analytics data.
    """
    # Extract channel from context (injected by executor)
    context = input_data.get("context", {})
    channel_data = context.get("channel")
    
    if not channel_data:
        logger.warning("fetch_last_video_analytics called without channel context")
        return ToolResult(
            tool_name="fetch_last_video_analytics",
            success=False,
            error="No channel context available. Please connect a YouTube channel first."
        )
    
    channel_id = channel_data.get("id")
    access_token = channel_data.get("access_token")
    channel_name = channel_data.get("channel_name", "Unknown")
    
    if not access_token:
        logger.error(f"No access_token for channel {channel_name}")
        return ToolResult(
            tool_name="fetch_last_video_analytics",
            success=False,
            error="Channel has no access_token. Please reconnect YouTube."
        )
    
    logger.info(f"[PRO] Fetching last video analytics for channel: {channel_name}")
    
    try:
        fetcher = YouTubeVideoFetcher(access_token)
        
        # Step 1: Get the latest video
        video = fetcher.get_latest_video()
        
        if not video:
            return ToolResult(
                tool_name="fetch_last_video_analytics",
                success=True,
                output={
                    "message": "No videos found on this channel.",
                    "data": None
                }
            )
        
        video_id = video["video_id"]
        title = video["title"]
        
        logger.info(f"[PRO] Latest video resolved: {video_id} - '{title}'")
        
        # Step 2: Get analytics for the video
        analytics = fetcher.get_video_analytics(video_id)
        
        # Step 3: Calculate engagement rate
        views = video["views"]
        likes = video["likes"]
        comments = video["comments"]
        
        if views > 0:
            engagement_rate = ((likes + comments) / views) * 100
        else:
            engagement_rate = 0.0
        
        # Use analytics avg_view_duration if available, otherwise estimate
        avg_watch_time_seconds = analytics.get("avg_view_duration_seconds", 0)
        
        # Step 4: Build normalized output
        normalized_data = {
            "video_id": video_id,
            "title": title,
            "published_at": video["published_at"],
            "views": views,
            "avg_watch_time_seconds": round(avg_watch_time_seconds, 2),
            "engagement_rate": round(engagement_rate, 2),
            # Additional metrics for richer context
            "likes": likes,
            "comments": comments
        }
        
        logger.info(
            f"[PRO] fetch_last_video_analytics completed: "
            f"video_id={video_id}, title='{title}', views={views}"
        )
        
        return ToolResult(
            tool_name="fetch_last_video_analytics",
            success=True,
            output={
                "message": "Last video analytics fetched successfully",
                "data": normalized_data
            }
        )
        
    except HttpError as e:
        logger.error(f"YouTube API error in fetch_last_video_analytics: {e}")
        return ToolResult(
            tool_name="fetch_last_video_analytics",
            success=False,
            error=f"YouTube API error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error in fetch_last_video_analytics: {e}")
        return ToolResult(
            tool_name="fetch_last_video_analytics",
            success=False,
            error=f"Unexpected error: {str(e)}"
        )
