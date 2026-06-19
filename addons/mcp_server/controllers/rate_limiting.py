import functools
import logging
import signal
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List

from odoo.http import request

_logger = logging.getLogger(__name__)

# Constants for rate limiting configuration
DEFAULT_REQUEST_LIMIT = 300
MINIMUM_REQUEST_LIMIT = 10
RATE_LIMIT_WINDOW_MINUTES = 1

# Cache for API request timestamps (user_id: [timestamps])
_api_request_cache: Dict[int, List[datetime]] = {}
# Lock for thread-safe cache access
_cache_lock = threading.Lock()


def get_request_limit():
    """
    Get request limit from system parameter `mcp_server.request_limit`.
    Default is 300 requests per minute per API key.
    Returns 0 to indicate unlimited requests.

    :return: The configured request limit per minute, or 0 for unlimited.
    :rtype: int
    """
    try:
        limit = int(
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mcp_server.request_limit", DEFAULT_REQUEST_LIMIT)
        )
        # 0 means unlimited, don't enforce minimum
        if limit == 0:
            return 0
        # For non-zero limits, ensure a sensible minimum
        return max(MINIMUM_REQUEST_LIMIT, limit)
    except (ValueError, TypeError) as e:
        _logger.error(f"Error parsing request limit: {e}. Using default value.")
        return DEFAULT_REQUEST_LIMIT


def record_api_request(user_id: int) -> None:
    """
    Record API request timestamp for rate limiting.

    :param user_id: The ID of the user making the request.
    :type user_id: int
    """
    now = datetime.now(timezone.utc)
    with _cache_lock:
        if user_id not in _api_request_cache:
            _api_request_cache[user_id] = []

        # Add current timestamp
        _api_request_cache[user_id].append(now)

        # Clean up old timestamps (older than 1 minute)
        one_minute_ago = now - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
        _api_request_cache[user_id] = [
            ts for ts in _api_request_cache[user_id] if ts > one_minute_ago
        ]


def check_rate_limit(user_id: int) -> bool:
    """
    Check if user has exceeded the configured request limit.

    :param user_id: The ID of the user making the request.
    :type user_id: int
    :return: True if the user is within the limit, False otherwise.
    :rtype: bool
    """
    limit = get_request_limit()

    # If limit is 0, allow unlimited requests
    if limit == 0:
        return True

    now = datetime.now(timezone.utc)
    one_minute_ago = now - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)

    with _cache_lock:
        if user_id not in _api_request_cache:
            return True  # No requests recorded yet

        # Filter requests in the last minute
        recent_requests = [
            ts for ts in _api_request_cache[user_id] if ts > one_minute_ago
        ]
        _api_request_cache[user_id] = recent_requests  # Update cache

        return len(recent_requests) < limit


def rate_limit(func):
    """
    Decorator enforcing request limits per minute per API key.
    Uses the system parameter `mcp_server.request_limit`
    for the limit value (default 300).
    Checks current usage for the user (identified by API key).
    Returns 429 error if exceeded.
    Updates usage counter.
    Assumes `require_api_key` decorator (or similar) is used before this one
    to ensure `kwargs['user']` is available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from . import response_utils

        # Check if rate limiting is enabled
        rate_limiting_enabled = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mcp_server.enable_rate_limiting", "True")
            == "True"
        )

        if not rate_limiting_enabled:
            return func(*args, **kwargs)

        # This decorator expects the user to be identified
        # and passed, typically by `require_api_key`
        user = kwargs.get("user")
        if not user:
            # For anonymous requests, use a special ID
            _logger.warning(
                "Rate limit decorator called without a user context. "
                "Using fallback anonymous rate limiting."
            )
            anonymous_id = -1
            if not check_rate_limit(anonymous_id):
                return response_utils.error_response(
                    "Too many anonymous requests. Please try again later.",
                    "E429",
                    status=429,
                )
            record_api_request(anonymous_id)
            return func(*args, **kwargs)

        if not check_rate_limit(user.id):
            # Log rate limit exceeded
            request.env["mcp.log"].sudo().log_rate_limit_exceeded(
                user_id=user.id,
                endpoint=request.httprequest.path,
                ip_address=request.httprequest.remote_addr,
            )
            return response_utils.error_response(
                "Too many requests. Please try again later.", "E429", status=429
            )

        record_api_request(user.id)
        return func(*args, **kwargs)

    return wrapper


class TimeoutError(Exception):
    """Exception raised when a request times out."""

    pass


def timeout_handler(signum, frame):
    """Signal handler for request timeout."""
    raise TimeoutError("Request processing exceeded timeout limit")


def request_timeout(func: Callable) -> Callable:
    """
    Decorator enforcing request timeout from
    `mcp_server.request_timeout` setting. Terminates request processing
     if it exceeds the configured timeout.

    IMPORTANT: This decorator cannot be used in web server contexts
    (like Odoo HTTP controllers) because signal.SIGALRM only works in the main
    thread, and web servers handle requests in worker threads. Attempting to use
    this decorator in HTTP controllers will result in "ValueError: signal only
    works in main thread of the main interpreter".

    This decorator is kept for reference but should not be used with
    Odoo HTTP endpoints. For web request timeouts, configure timeouts at the web
    server level (nginx, Apache, etc.) or use Odoo's built-in request
    timeout mechanisms.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from . import response_utils

        # Get timeout setting
        try:
            timeout_seconds = int(
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("mcp_server.request_timeout", "30")
            )
        except (ValueError, TypeError):
            timeout_seconds = 30

        # If timeout is 0 or negative, don't enforce timeout
        if timeout_seconds <= 0:
            return func(*args, **kwargs)

        # Only use signal-based timeout on Unix-like systems
        if hasattr(signal, "SIGALRM"):
            # Save the old handler
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                result = func(*args, **kwargs)
                # Cancel the alarm
                signal.alarm(0)
                return result
            except TimeoutError:
                _logger.warning(f"Request timeout after {timeout_seconds} seconds")
                return response_utils.error_response(
                    f"Request processing exceeded timeout "
                    f"limit of {timeout_seconds} seconds.",
                    "E408",
                    status=408,  # Request Timeout
                )
            finally:
                # Restore the old handler
                signal.signal(signal.SIGALRM, old_handler)
                signal.alarm(0)
        else:
            # On non-Unix systems, just execute without timeout
            _logger.debug("Request timeout not supported on this platform")
            return func(*args, **kwargs)

    return wrapper
