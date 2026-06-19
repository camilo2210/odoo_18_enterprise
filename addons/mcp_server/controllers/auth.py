"""Authentication utilities for MCP Server."""

import functools
import logging

from odoo.http import request

_logger = logging.getLogger(__name__)


def get_user_from_api_key(api_key):
    """
    Get user from API key.

    :param api_key: The API key to validate
    :return: res.users record or None
    """
    if not api_key:
        return None

    try:
        user_id = (
            request.env["res.users.apikeys"]
            .sudo()  # sudo: validate API key without user context
            ._check_credentials(scope="rpc", key=api_key)
        )
        if not user_id:
            # sudo: write to mcp.log regardless of user permissions
            request.env["mcp.log"].sudo().log_authentication(
                success=False,
                api_key_used=True,
                ip_address=request.httprequest.remote_addr,
                error_message="Invalid API key",
            )
            return None
        # sudo: browse user by ID without requiring existing user context
        user = request.env["res.users"].sudo().browse(user_id).exists()
        if user and user.active:
            # sudo: write to mcp.log regardless of user permissions
            request.env["mcp.log"].sudo().log_authentication(
                success=True,
                user_id=user.id,
                api_key_used=True,
                ip_address=request.httprequest.remote_addr,
            )
            return user
        else:
            # sudo: write to mcp.log regardless of user permissions
            request.env["mcp.log"].sudo().log_authentication(
                success=False,
                api_key_used=True,
                ip_address=request.httprequest.remote_addr,
                error_message="User not found or inactive",
            )
            return None
    except Exception as e:
        _logger.warning(f"Error validating API key: {e}")
        # sudo: write to mcp.log regardless of user permissions
        request.env["mcp.log"].sudo().log_authentication(
            success=False,
            api_key_used=True,
            ip_address=request.httprequest.remote_addr,
            error_message=str(e),
        )
        return None


def validate_api_key(req):
    """
    Validate API key from request headers.

    :param req: The HTTP request object
    :return: User record if valid, None otherwise
    """
    api_key = req.httprequest.headers.get("X-API-Key")
    if not api_key:
        return None

    return get_user_from_api_key(api_key)


def get_user_from_session():
    """
    Get user from the current Odoo session.

    With auth="public" routes, Odoo resolves the session automatically
    when a valid session_id cookie is present.

    :return: res.users record or None
    """
    try:
        user = request.env.user
        if user and user.id and user.id != request.env.ref("base.public_user").id:
            return user
    except Exception as e:
        _logger.debug("Session auth check failed: %s", e)
    return None


def require_auth(func):
    """
    Decorator for endpoints requiring authentication.

    Checks authentication in order:
    1. X-API-Key header
    2. Odoo session cookie (if user is logged in)
    3. Rejects with 401
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from . import response_utils

        # 1. Try API key authentication
        user = validate_api_key(request)

        # 2. Fall back to session authentication
        if not user:
            user = get_user_from_session()

        # 3. No valid authentication found
        if not user:
            # sudo: write to mcp.log regardless of user permissions
            request.env["mcp.log"].sudo().log_authentication(
                success=False,
                api_key_used=False,
                ip_address=request.httprequest.remote_addr,
                error_message="No valid API key or session",
            )
            return response_utils.error_response(
                "Authentication required. Provide a valid API key "
                "(X-API-Key header) or session cookie.",
                "E401",
                status=401,
            )

        kwargs["user"] = user
        return func(*args, **kwargs)

    return wrapper


# Backwards compatibility alias
require_api_key = require_auth
