"""Response utilities for MCP Server."""

import logging
from datetime import datetime, timezone

from odoo.http import request

_logger = logging.getLogger(__name__)

# Standard error codes
ERROR_CODES = {
    400: "E400",  # Bad Request
    401: "E401",  # Unauthorized
    403: "E403",  # Forbidden
    404: "E404",  # Not Found
    429: "E429",  # Too Many Requests
    500: "E500",  # Internal Server Error
    503: "E503",  # Service Unavailable
}


def get_timestamp():
    """
    Get current timestamp in ISO format.

    :return: ISO formatted timestamp string
    :rtype: str
    """
    return datetime.now(timezone.utc).isoformat()


def success_response(data, meta=None):
    """
    Format successful API response following the specification.
    Always include timestamp in meta.
    Format: {"success": true, "data": {...}, "meta": {...}}

    :param data: The data payload for the response
    :type data: dict
    :param meta: Optional metadata for the response
    :type meta: dict, optional
    :return: JSON response for success
    :rtype: odoo.http.Response
    """
    # Ensure data is a dict
    if data is None:
        data = {}
    elif not isinstance(data, dict):
        try:
            # Try to convert to dict if possible
            data = dict(data)
        except (TypeError, ValueError):
            # Wrap in a dictionary if conversion fails
            data = {"result": data}

    # Prepare metadata
    response_meta = {"timestamp": get_timestamp()}
    if meta and isinstance(meta, dict):
        response_meta.update(meta)

    payload = {"success": True, "data": data, "meta": response_meta}

    # Ensure Content-Type is application/json
    headers = {
        "Content-Type": "application/json",
    }

    return request.make_json_response(payload, headers=headers)


def error_response(message, code=None, status=400, meta=None):
    """
    Format error API response following the specification.
    Always include timestamp in meta.
    Format:
        {
            "success": false,
            "error": {"message": "...", "code": "..."},
            "meta": {...}
        }

    :param message: The error message
    :type message: str
    :param code: The error code (e.g., "E400"). If None, derives from status
    :type code: str, optional
    :param status: The HTTP status code for the response
    :type status: int
    :param meta: Optional metadata for the response
    :type meta: dict, optional
    :return: JSON response for error
    :rtype: odoo.http.Response
    """
    # Ensure message is a string
    message = str(message) if message else "Unknown error"

    # Derive code from status if not provided
    if not code:
        code = ERROR_CODES.get(status, f"E{status}")

    # Prepare metadata
    response_meta = {"timestamp": get_timestamp()}
    if meta and isinstance(meta, dict):
        response_meta.update(meta)

    payload = {
        "success": False,
        "error": {"message": message, "code": code},
        "meta": response_meta,
    }

    # Ensure Content-Type is application/json
    headers = {
        "Content-Type": "application/json",
    }

    return request.make_json_response(payload, status=status, headers=headers)
