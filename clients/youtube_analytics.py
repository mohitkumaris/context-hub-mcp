"""
YouTube Analytics API Client.

Provides OAuth-authenticated access to the YouTube Analytics API
using stored access tokens from the channels table.
"""

import logging
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class YouTubeAnalyticsClient:
    """
    YouTube Analytics API client using OAuth credentials.
    
    Uses stored access_token from the channels table to authenticate
    API requests. Does not use API keys.
    """
    
    # YouTube Analytics API configuration
    API_SERVICE_NAME = "youtubeAnalytics"
    API_VERSION = "v2"
    
    def __init__(self, access_token: str) -> None:
        """
        Initialize the YouTube Analytics client.
        
        Args:
            access_token: OAuth access token from the channels table.
        """
        self.access_token = access_token
        self._service = None
        logger.info("YouTubeAnalyticsClient initialized")
    
    def _build_credentials(self) -> Credentials:
        """
        Build Google OAuth credentials from access token.
        
        Returns:
            Credentials object for API authentication.
        """
        return Credentials(token=self.access_token)
    
    def _get_service(self) -> Any:
        """
        Get or create the YouTube Analytics API service.
        
        Returns:
            YouTube Analytics API service instance.
        """
        if self._service is None:
            credentials = self._build_credentials()
            self._service = build(
                self.API_SERVICE_NAME,
                self.API_VERSION,
                credentials=credentials,
                cache_discovery=False  # Required to avoid caching issues
            )
            logger.debug("YouTube Analytics API service built successfully")
        return self._service
    
    def query_reports(
        self,
        start_date: str,
        end_date: str,
        metrics: str,
        dimensions: Optional[str] = None,
        filters: Optional[str] = None,
        sort: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Query the YouTube Analytics reports API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            metrics: Comma-separated list of metrics to retrieve.
            dimensions: Optional comma-separated list of dimensions.
            filters: Optional filters for the query.
            sort: Optional sort order.
            
        Returns:
            Raw API response as dictionary.
            
        Raises:
            HttpError: If the API request fails.
        """
        service = self._get_service()
        
        # Build the query parameters
        query_params = {
            "ids": "channel==MINE",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": metrics
        }
        
        if dimensions:
            query_params["dimensions"] = dimensions
        if filters:
            query_params["filters"] = filters
        if sort:
            query_params["sort"] = sort
        
        logger.info(
            f"Calling YouTube Analytics API: "
            f"metrics={metrics}, dimensions={dimensions}, "
            f"startDate={start_date}, endDate={end_date}"
        )
        
        try:
            response = service.reports().query(**query_params).execute()
            logger.debug(f"YouTube Analytics API response received: {len(response.get('rows', []))} rows")
            return response
        except HttpError as e:
            logger.error(f"YouTube Analytics API error: {e}")
            raise
