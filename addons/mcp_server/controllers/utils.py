import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

import odoo
from odoo import modules
from odoo.api import Environment
from odoo.http import request

_logger = logging.getLogger(__name__)

# Constants for configuration
CACHE_TTL_SECONDS = 300  # 5 minutes

# Cache for MCP enabled status (TTL: 5 minutes)
_mcp_enabled_cache: Dict[str, Optional[Union[datetime, bool]]] = {
    "timestamp": None,
    "value": None,
}

# Cache for model access checks (model_name: {'timestamp': datetime, 'value': bool})
_model_enabled_cache: Dict[str, Dict[str, Union[datetime, bool]]] = {}

# Cache for operation access checks (model_name-operation:
# {'timestamp': datetime, 'value': bool})
_operation_enabled_cache: Dict[str, Dict[str, Union[datetime, bool]]] = {}


def clear_mcp_caches() -> None:
    """
    Clear all MCP-related caches.

    This function should be called when MCP configuration changes
    to ensure fresh data is loaded.
    """
    global _mcp_enabled_cache, _model_enabled_cache, _operation_enabled_cache
    _mcp_enabled_cache = {"timestamp": None, "value": None}
    _model_enabled_cache.clear()
    _operation_enabled_cache.clear()
    _logger.info("MCP caches cleared")


def sanitize_model_name(model_name: str) -> str:
    """
    Sanitize and validate model name.

    :param model_name: The model name to sanitize
    :type model_name: str
    :return: Sanitized model name
    :rtype: str
    :raises ValueError: If model name is invalid
    """
    if not model_name:
        raise ValueError("Model name cannot be empty")
    # Basic validation: only allow alphanumeric, dots, and underscores
    if not re.match(r"^[a-zA-Z0-9._]+$", model_name):
        raise ValueError(f"Invalid model name format: {model_name}")

    return model_name.strip()


def is_mcp_enabled() -> bool:
    """
    Check if MCP is globally enabled via `mcp_server.enabled` system parameter.
    Result is cached for 5 minutes to reduce database queries.

    :return: True if MCP is enabled, False otherwise.
    :rtype: bool
    """
    now = datetime.now(timezone.utc)

    # Check if cache is valid
    if (
        _mcp_enabled_cache["timestamp"] is not None
        and (now - _mcp_enabled_cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS
    ):
        return _mcp_enabled_cache["value"]

    # Get fresh value
    try:
        value = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mcp_server.enabled", "False")
            == "True"
        )

        # Update cache
        _mcp_enabled_cache["timestamp"] = now
        _mcp_enabled_cache["value"] = value

        return value
    except Exception as e:
        _logger.error(f"Error checking if MCP is enabled: {e}")
        return False


def is_model_mcp_enabled(env: Environment, model_name: str) -> bool:
    """
    Check if a specific model is MCP-enabled.
    Uses existing `mcp.enabled.model.is_model_enabled()` method.
    Result is cached for 5 minutes to reduce database queries.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :param model_name: The technical name of the model (e.g., "res.partner").
    :type model_name: str
    :return: True if the model is MCP-enabled, False otherwise.
    :rtype: bool
    """
    if not is_mcp_enabled():  # Check global switch first
        return False

    now = datetime.now(timezone.utc)

    # Normalize and validate model name
    try:
        model_name = sanitize_model_name(model_name)
    except ValueError as e:
        _logger.warning(f"Invalid model name: {e}")
        return False

    # Check if cache is valid
    if (
        model_name in _model_enabled_cache
        and (now - _model_enabled_cache[model_name]["timestamp"]).total_seconds()
        < CACHE_TTL_SECONDS
    ):
        return _model_enabled_cache[model_name]["value"]

    # Get fresh value
    try:
        value = env["mcp.enabled.model"].sudo().is_model_enabled(model_name)

        # Update cache
        _model_enabled_cache[model_name] = {"timestamp": now, "value": value}

        return value
    except Exception as e:
        _logger.error(f"Error checking if model {model_name} is MCP-enabled: {e}")
        return False


def check_model_operation_allowed(
    env: Environment, model_name: str, operation: str
) -> bool:
    """
    Check if a specific operation is allowed for an MCP-enabled model.
    Uses existing `mcp.enabled.model.check_model_operation_enabled()` method.
    Result is cached for 5 minutes to reduce database queries.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :param model_name: The technical name of the model.
    :type model_name: str
    :param operation: The operation to check
    (e.g., "read", "create", "write", "unlink").
    :type operation: str
    :return: True if the operation is allowed, False otherwise.
    :rtype: bool
    """
    if not is_mcp_enabled():  # Check global switch first
        return False

    # Normalize and validate inputs
    try:
        model_name = sanitize_model_name(model_name)
    except ValueError as e:
        _logger.warning(f"Invalid model name: {e}")
        return False

    operation = str(operation).strip().lower()

    # Check if the operation is valid
    valid_operations = ["read", "create", "write", "unlink"]
    if operation not in valid_operations:
        _logger.warning(
            f"Invalid operation '{operation}' requested for model '{model_name}'"
        )
        return False

    # Check if model is enabled first (uses cache)
    if not is_model_mcp_enabled(env, model_name):
        return False

    now = datetime.now(timezone.utc)
    cache_key = f"{model_name}-{operation}"

    # Check if cache is valid
    if (
        cache_key in _operation_enabled_cache
        and (now - _operation_enabled_cache[cache_key]["timestamp"]).total_seconds()
        < CACHE_TTL_SECONDS
    ):
        return _operation_enabled_cache[cache_key]["value"]

    # Get fresh value
    try:
        value = (
            env["mcp.enabled.model"]
            .sudo()
            .check_model_operation_enabled(model_name, operation)
        )

        # Update cache
        _operation_enabled_cache[cache_key] = {"timestamp": now, "value": value}

        return value
    except Exception as e:
        message = (
            f"Error checking if operation {operation} "
            f"is allowed for model {model_name}: {e}"
        )
        _logger.error(message)
        return False


def get_enabled_models(env: Environment) -> List[Dict[str, str]]:
    """
    Get a list of all MCP-enabled models with their display names.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :return: List of dictionaries, each with "model"
    (technical name) and "name" (display name).
    :rtype: list[dict]
    """
    if not is_mcp_enabled():
        return []

    try:
        enabled_model_records = (
            env["mcp.enabled.model"].sudo().search([("active", "=", True)])
        )

        # Batch fetch all model names to avoid N+1 queries
        model_names = enabled_model_records.mapped("model_name")
        ir_models = env["ir.model"].sudo().search([("model", "in", model_names)])

        # Create a mapping for quick lookup
        model_name_map = {m.model: m.name for m in ir_models}

        models_info = []
        for record in enabled_model_records:
            if record.model_name in model_name_map:
                models_info.append(
                    {
                        "model": record.model_name,
                        "name": model_name_map[record.model_name],
                    }
                )
            else:
                _logger.warning(f"Model {record.model_name} not found in ir.model")

        return models_info
    except Exception as e:
        _logger.error(f"Error fetching enabled models: {e}")
        return []


def get_model_allowed_operations(env: Environment, model_name: str) -> Dict[str, bool]:
    """
    Get a dictionary of allowed operations for a specific MCP-enabled model.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :param model_name: The technical name of the model.
    :type model_name: str
    :return: Dictionary with operation names as keys and boolean values
             indicating if allowed. Returns an empty dict if model is
             not found or not MCP enabled.
    :rtype: dict
    """
    if not is_mcp_enabled():
        return {}

    try:
        model_name = sanitize_model_name(model_name)
    except ValueError:
        return {}

    mcp_model_record = (
        env["mcp.enabled.model"]
        .sudo()
        .search([("model_name", "=", model_name), ("active", "=", True)], limit=1)
    )

    if not mcp_model_record:
        return {}

    return {
        "read": mcp_model_record.allow_read,
        "create": mcp_model_record.allow_create,
        "write": mcp_model_record.allow_write,
        "unlink": mcp_model_record.allow_unlink,
    }


XMLRPC_METHOD_OPERATION_MAP = {
    # Read operations
    "read": "read",
    "search": "read",
    "search_read": "read",
    "search_count": "read",
    "name_search": "read",
    "fields_get": "read",
    "export_data": "read",
    "default_get": "read",
    "name_get": "read",
    "get_metadata": "read",
    "get_formview_id": "read",
    "get_formview_action": "read",
    "read_group": "read",
    # Create operations
    "create": "create",
    "copy": "create",
    "name_create": "create",
    # Write operations
    "write": "write",
    "toggle_active": "write",
    "action_archive": "write",
    "action_unarchive": "write",
    "message_post": "write",
    # Unlink operations
    "unlink": "unlink",
    "action_delete": "unlink",
    "button_immediate_uninstall": "unlink",
}


def map_method_to_operation(method: str) -> Optional[str]:
    """
    Map XML-RPC method to operation type (read/write/create/unlink).

    :param method: The XML-RPC method name (e.g., "search_read").
    :type method: str
    :return: The corresponding operation type or None if not mapped.
    :rtype: str | None
    """
    # Sanitize method name
    method = str(method).lower().strip()
    return XMLRPC_METHOD_OPERATION_MAP.get(method)


def check_mcp_access(env: Environment, model_name: str, method_name: str) -> bool:
    """
    Check if an XML-RPC method is allowed for a given model via MCP configuration.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :param model_name: The technical name of the model.
    :type model_name: str
    :param method_name: The XML-RPC method name.
    :type method_name: str
    :return: True if the method is allowed, False otherwise.
    :rtype: bool
    """
    # Sanitize inputs
    if not model_name or not method_name:
        _logger.warning(
            f"MCP: Invalid model or method name: {model_name}, {method_name}"
        )
        return False

    try:
        model_name = sanitize_model_name(model_name)
    except ValueError as e:
        _logger.warning(f"MCP: {e}")
        return False

    method_name = str(method_name).strip()

    if not is_mcp_enabled():  # Global check
        _logger.info("MCP: Access denied because MCP is globally disabled.")
        return False

    # Check if model exists to prevent errors
    model_exists = bool(
        env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
    )
    if not model_exists:
        message = f"MCP: Model {model_name} does not exist in this Odoo instance."
        _logger.warning(message)
        return False

    if not env["mcp.enabled.model"].sudo().is_model_enabled(model_name):
        message = (
            f"MCP: Access denied for XML-RPC method '{method_name}' "
            f"on model '{model_name}'. Model not MCP enabled."
        )
        _logger.info(message)
        return False

    operation = map_method_to_operation(method_name)
    if not operation:
        message = (
            f"MCP: XML-RPC method '{method_name}' on model '{model_name}' "
            f"has no defined MCP operation mapping. Access denied by default."
        )
        _logger.warning(message)
        return False

    # Check if operation is allowed for this model
    operation_allowed = (
        env["mcp.enabled.model"]
        .sudo()
        .check_model_operation_enabled(model_name, operation)
    )

    if not operation_allowed:
        message = (
            f"MCP: Access denied for XML-RPC method '{method_name}' "
            f"(operation '{operation}') on model '{model_name}'. "
            f"Operation not allowed by MCP."
        )
        _logger.info(message)
        return False

    # Additional security check: Don't allow methods that start
    # with underscore (private methods)
    if method_name.startswith("_"):
        _logger.warning(
            f"MCP: Attempted access to private method {method_name}. Access denied."
        )
        return False

    # Log successful access
    message = (
        f"MCP: Access granted for XML-RPC method '{method_name}'"
        f" (operation '{operation}') on model '{model_name}'."
    )
    _logger.debug(message)

    return True


def get_allowed_xmlrpc_methods() -> List[str]:
    """
    Get a list of all XML-RPC methods that are mapped to MCP operations.
    This primarily serves as an informational list of methods MCP actively considers.

    :return: List of XML-RPC method names.
    :rtype: list[str]
    """
    return list(XMLRPC_METHOD_OPERATION_MAP.keys())


def get_mcp_server_version() -> str:
    """
    Return the current MCP server version from the module's manifest.

    :return: The MCP server version string.
    :rtype: str
    """
    # Get version from manifest
    try:
        manifest = modules.module.get_manifest("mcp_server")
        version = manifest.get("version", "1.0.0")
        return version
    except Exception as e:
        _logger.error(f"Error retrieving MCP server version from manifest: {e}")
        return "1.0.0"  # Fallback version


def get_system_info(env: Environment) -> Dict[str, Union[str, int]]:
    """
    Get system information including Odoo version, DB name, language,
    enabled MCP models count, MCP server version, and server timezone.

    :param env: Odoo environment.
    :type env: odoo.api.Environment
    :return: Dictionary containing system information.
    :rtype: dict
    """
    db_name = env.cr.dbname
    odoo_version = odoo.release.version

    # Current user's language or system default
    lang = env.context.get("lang")
    if not lang and env.user:
        lang = env.user.lang
    if not lang:  # Fallback if no user context or user has no lang
        lang = (
            env["ir.default"].sudo().get("res.partner", "lang")
        )  # A common place for default lang
    if not lang:  # Further fallback
        lang = env["ir.config_parameter"].sudo().get_param("base.language", "en_US")

    enabled_mcp_models_count = 0
    if is_mcp_enabled():  # Only count if MCP is globally on
        enabled_mcp_models_count = (
            env["mcp.enabled.model"].sudo().search_count([("active", "=", True)])
        )

    server_timezone = env.context.get("tz")  # Get timezone from context
    if not server_timezone and env.user:
        server_timezone = env.user.tz
    if not server_timezone:  # Fallback to UTC if not set
        server_timezone = "UTC"

    return {
        "db_name": db_name,
        "odoo_version": odoo_version,
        "language": lang,
        "enabled_mcp_models": enabled_mcp_models_count,
        "mcp_server_version": get_mcp_server_version(),
        "server_timezone": server_timezone,
    }
