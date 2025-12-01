"""
Authentication Handler for External APIs

Supports multiple authentication mechanisms:
- API Key (header or query parameter)
- Bearer Token
- Basic Authentication
- OAuth2 Client Credentials
"""

import base64
import logging
from typing import Dict, Optional, Tuple
import httpx
from datetime import datetime, timedelta

from app.models.schemas import IntegrationAuthConfig

logger = logging.getLogger(__name__)


class AuthHandler:
    """
    Handles authentication for external API calls

    Usage:
        auth_handler = AuthHandler(auth_config)
        headers, query_params = await auth_handler.get_auth_headers_and_params()
    """

    def __init__(self, auth_config: IntegrationAuthConfig):
        self.auth_config = auth_config
        self._oauth2_token: Optional[str] = None
        self._oauth2_token_expires: Optional[datetime] = None

    async def get_auth_headers_and_params(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Get authentication headers and query parameters

        Returns:
            Tuple of (headers, query_params)
        """
        headers = {}
        query_params = {}

        if self.auth_config.auth_type == "none":
            return headers, query_params

        elif self.auth_config.auth_type == "api_key":
            if self.auth_config.api_key_header:
                headers[self.auth_config.api_key_header] = self.auth_config.api_key_value
            else:
                # Default to Authorization header
                headers["X-API-Key"] = self.auth_config.api_key_value

        elif self.auth_config.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.auth_config.bearer_token}"

        elif self.auth_config.auth_type == "basic":
            credentials = f"{self.auth_config.basic_username}:{self.auth_config.basic_password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif self.auth_config.auth_type == "oauth2":
            token = await self._get_oauth2_token()
            headers["Authorization"] = f"Bearer {token}"

        return headers, query_params

    async def _get_oauth2_token(self) -> str:
        """
        Get OAuth2 token using client credentials flow

        Implements token caching and automatic renewal
        """
        # Check if we have a valid cached token
        if self._oauth2_token and self._oauth2_token_expires:
            if datetime.utcnow() < self._oauth2_token_expires:
                return self._oauth2_token

        # Request new token
        logger.info(f"Requesting new OAuth2 token from {self.auth_config.oauth2_token_url}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.auth_config.oauth2_token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.auth_config.oauth2_client_id,
                    "client_secret": self.auth_config.oauth2_client_secret,
                    "scope": self.auth_config.oauth2_scope or ""
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            if response.status_code != 200:
                logger.error(f"OAuth2 token request failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to obtain OAuth2 token: {response.status_code}")

            token_data = response.json()
            self._oauth2_token = token_data["access_token"]

            # Calculate expiration (with 5 minute buffer)
            expires_in = token_data.get("expires_in", 3600)
            self._oauth2_token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)

            logger.info(f"OAuth2 token obtained, expires at {self._oauth2_token_expires}")

            return self._oauth2_token

    def clear_cache(self):
        """Clear cached OAuth2 token (useful for testing or force refresh)"""
        self._oauth2_token = None
        self._oauth2_token_expires = None
