"""Canary API authentication and session management module."""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar("T")


class CanaryAuthError(Exception):
    """Exception raised for authentication errors."""

    pass


def retry_with_backoff(
    max_attempts: Optional[int] = None,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that implements retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default from env or 3)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation

    Returns:
        Decorated function with retry logic
    """
    if max_attempts is None:
        max_attempts = int(os.getenv("CANARY_RETRY_ATTEMPTS", "3"))

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    await asyncio.sleep(delay)

                except CanaryAuthError:
                    # Don't retry authentication errors (likely bad credentials)
                    raise

                except Exception as e:
                    # Log unexpected errors but don't retry
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Retry logic failed unexpectedly for {func.__name__}")

        return wrapper

    return decorator


class CanaryAuthClient:
    """
    Manages authentication and session tokens for Canary Views Web API.

    Handles token-based authentication, automatic token refresh before expiry,
    and credential management from environment variables.
    """

    def __init__(self) -> None:
        """Initialize the Canary authentication client."""
        # Load credentials from environment
        self.saf_base_url = os.getenv("CANARY_SAF_BASE_URL", "")
        self.views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        self.user_token = os.getenv("CANARY_API_TOKEN", "")

        # Session configuration
        self.session_timeout_ms = int(
            os.getenv("CANARY_SESSION_TIMEOUT_MS", "120000")
        )
        self.request_timeout = int(os.getenv("CANARY_REQUEST_TIMEOUT_SECONDS", "10"))

        # Session state
        self._session_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "CanaryAuthClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.request_timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _validate_credentials(self) -> None:
        """
        Validate that all required credentials are present.

        Raises:
            CanaryAuthError: If any required credentials are missing
        """
        missing_creds = []

        if not self.saf_base_url:
            missing_creds.append("CANARY_SAF_BASE_URL")
        if not self.views_base_url:
            missing_creds.append("CANARY_VIEWS_BASE_URL")
        if not self.user_token:
            missing_creds.append("CANARY_API_TOKEN")

        if missing_creds:
            raise CanaryAuthError(
                f"Missing required credentials: {', '.join(missing_creds)}. "
                "Please set these environment variables in your .env file."
            )

    def is_token_expired(self) -> bool:
        """
        Check if the current session token is expired or will expire soon.

        Returns:
            bool: True if token is expired or will expire in <30 seconds
        """
        if not self._session_token or not self._token_expires_at:
            return True

        # Refresh if less than 30 seconds remaining
        time_remaining = self._token_expires_at - datetime.now()
        return time_remaining.total_seconds() < 30

    @retry_with_backoff()
    async def _do_authenticate_request(self) -> str:
        """
        Perform the actual authentication HTTP request with retry logic.

        This method has retry logic applied via decorator.
        ConnectError and TimeoutException are NOT wrapped so retry can catch them.

        Returns:
            str: The session token

        Raises:
            httpx.ConnectError: Connection failures (retried automatically)
            httpx.TimeoutException: Timeout failures (retried automatically)
            CanaryAuthError: Other authentication failures (not retried)
        """
        if not self._client:
            raise CanaryAuthError(
                "HTTP client not initialized. Use 'async with' context manager."
            )

        # Construct authentication endpoint
        auth_url = f"{self.saf_base_url}/getSessionToken"

        try:
            response = await self._client.post(
                auth_url,
                json={"userToken": self.user_token},
            )

            response.raise_for_status()

            data = response.json()

            # Extract session token
            session_token_raw = data.get("sessionToken")
            if not session_token_raw or not isinstance(session_token_raw, str):
                raise CanaryAuthError(
                    "Authentication response missing or invalid 'sessionToken' field"
                )

            # Type narrowing for mypy
            session_token = cast(str, session_token_raw)

            # Calculate token expiry
            # Session timeout is in milliseconds
            expiry_seconds = self.session_timeout_ms / 1000
            self._token_expires_at = datetime.now() + timedelta(seconds=expiry_seconds)

            self._session_token = session_token

            return session_token

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CanaryAuthError(
                    "Authentication failed: Invalid API token. "
                    "Please check your CANARY_API_TOKEN environment variable."
                ) from e
            elif e.response.status_code == 404:
                raise CanaryAuthError(
                    f"Authentication endpoint not found: {auth_url}. "
                    "Please check your CANARY_SAF_BASE_URL configuration."
                ) from e
            else:
                raise CanaryAuthError(
                    f"Authentication failed with HTTP {e.response.status_code}: {e.response.text}"
                ) from e

        except (httpx.ConnectError, httpx.TimeoutException):
            # Let these bubble up so retry decorator can catch them
            raise

        except Exception as e:
            raise CanaryAuthError(f"Unexpected authentication error: {str(e)}") from e

    async def authenticate(self) -> str:
        """
        Authenticate with Canary API and obtain a session token.

        Implements automatic retry with exponential backoff for connection failures.

        Returns:
            str: The session token

        Raises:
            CanaryAuthError: If authentication fails
        """
        self._validate_credentials()

        try:
            result = await self._do_authenticate_request()
            return cast(str, result)
        except httpx.ConnectError as e:
            # After all retries exhausted, wrap in CanaryAuthError
            raise CanaryAuthError(
                f"Cannot connect to Canary server at {self.saf_base_url}. "
                "Please check your network connection and server URL."
            ) from e
        except httpx.TimeoutException as e:
            # After all retries exhausted, wrap in CanaryAuthError
            raise CanaryAuthError(
                f"Authentication request timed out after {self.request_timeout} seconds. "
                "Please check your network connection or increase timeout."
            ) from e

    async def refresh_token(self) -> str:
        """
        Refresh the session token.

        This is essentially re-authenticating to get a new session token.

        Returns:
            str: The new session token

        Raises:
            CanaryAuthError: If token refresh fails
        """
        return await self.authenticate()

    async def get_valid_token(self) -> str:
        """
        Get a valid session token, refreshing if necessary.

        This method checks if the current token is expired or will expire soon,
        and automatically refreshes it if needed.

        Returns:
            str: A valid session token

        Raises:
            CanaryAuthError: If token retrieval or refresh fails
        """
        if self.is_token_expired():
            return await self.refresh_token()

        if not self._session_token:
            # Should not happen if is_token_expired works correctly
            return await self.authenticate()

        return self._session_token


async def validate_config() -> bool:
    """
    Validate Canary configuration and test API connection.

    Checks that all required environment variables are present and attempts
    to authenticate with the Canary API to verify the connection works.

    Returns:
        bool: True if configuration is valid and connection succeeds

    Raises:
        CanaryAuthError: If configuration is invalid or connection fails
    """
    logger.info("Validating Canary configuration...")

    async with CanaryAuthClient() as client:
        try:
            # Validate credentials (will raise if missing)
            client._validate_credentials()
            logger.info("✓ All required credentials present")

            # Test authentication
            await client.authenticate()
            logger.info("✓ Successfully authenticated with Canary API")
            logger.info(f"✓ Session token obtained (expires in {client.session_timeout_ms}ms)")

            return True

        except CanaryAuthError as e:
            logger.error(f"✗ Configuration validation failed: {str(e)}")
            raise
