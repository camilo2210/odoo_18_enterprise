import logging
import xmlrpc.client as xmlrpclib  # nosec
from datetime import datetime
from typing import Any, Optional, Tuple

import defusedxml.xmlrpc

from odoo import http
from odoo.addons.base.controllers.rpc import dumps as odoo_dumps
from odoo.http import request
from odoo.service import (
    common as common_service_root,
    db as db_service_root,
    model as model_service_root,
)

from . import auth, utils
from .rate_limiting import check_rate_limit, record_api_request

_logger = logging.getLogger(__name__)
defusedxml.xmlrpc.monkey_patch()

# XML-RPC fault codes aligned with HTTP status codes
XMLRPC_FAULT_CODES = {
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
    "rate_limit": 429,
    "internal_error": 500,
}


def _generate_xmlrpc_fault(code: int, message: str) -> str:
    """
    Helper to generate an XML-RPC fault string with standardized codes.

    :param code: The fault code (HTTP status code)
    :type code: int
    :param message: The fault message
    :type message: str
    :return: XML-RPC fault response string
    :rtype: str
    """
    fault = xmlrpclib.Fault(code, message)
    return xmlrpclib.dumps(fault, methodresponse=1, allow_none=1)


def _get_client_ip() -> Optional[str]:
    """Get client IP address from request."""
    if request and hasattr(request, "httprequest"):
        return request.httprequest.remote_addr
    return None


class MCPCommonController(http.Controller):
    @http.route(
        "/mcp/xmlrpc/common", type="http", auth="none", methods=["POST"], csrf=False
    )
    def index(self, **kwargs):
        # Check if MCP is globally enabled
        if not utils.is_mcp_enabled():
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["forbidden"],
                "MCP Server is disabled globally.",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])

        data = request.httprequest.data
        try:
            params, method = xmlrpclib.loads(data)
            result = common_service_root.dispatch(method, params)
            response_data = xmlrpclib.dumps((result,), methodresponse=1, allow_none=1)
            return request.make_response(response_data, [("Content-Type", "text/xml")])
        except xmlrpclib.Fault as e:
            _logger.warning(
                f"MCPCommonController XML-RPC Fault: "
                f"Code {e.faultCode}, String: {e.faultString}"
            )
            return request.make_response(
                xmlrpclib.dumps(e, methodresponse=1, allow_none=1),
                [("Content-Type", "text/xml")],
            )
        except Exception as e:
            error_msg = str(e)
            _logger.error("Error in MCPCommonController: %s", error_msg, exc_info=True)
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["internal_error"],
                f"MCPCommonController Error: {error_msg}",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])


class MCPDatabaseController(http.Controller):
    @http.route(
        "/mcp/xmlrpc/db", type="http", auth="none", methods=["POST"], csrf=False
    )
    def index(self, **kwargs):
        # Check if MCP is globally enabled
        if not utils.is_mcp_enabled():
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["forbidden"],
                "MCP Server is disabled globally.",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])

        data = request.httprequest.data
        try:
            params, method = xmlrpclib.loads(data)
            result = db_service_root.dispatch(method, params)
            response_data = xmlrpclib.dumps((result,), methodresponse=1, allow_none=1)
            return request.make_response(response_data, [("Content-Type", "text/xml")])
        except xmlrpclib.Fault as e:
            _logger.warning(
                f"MCPDatabaseController XML-RPC Fault: "
                f"Code {e.faultCode}, String: {e.faultString}"
            )
            return request.make_response(
                xmlrpclib.dumps(e, methodresponse=1, allow_none=1),
                [("Content-Type", "text/xml")],
            )
        except Exception as e:
            error_msg = str(e)
            _logger.error(
                "Error in MCPDatabaseController: %s", error_msg, exc_info=True
            )
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["internal_error"],
                f"MCPDatabaseController Error: {error_msg}",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])


class MCPObjectController(http.Controller):
    def _validate_request(self, xmlrpc_method: str, params: list) -> None:
        """
        Validate XML-RPC method and parameters.

        :param xmlrpc_method: The XML-RPC method name
        :param params: The XML-RPC parameters
        :raises xmlrpclib.Fault: If validation fails
        """
        if xmlrpc_method != "execute_kw":
            _logger.warning(
                f"MCPObjectController received non-execute_kw method: {xmlrpc_method}"
            )
            if request and hasattr(request, "env"):
                request.env["mcp.log"].sudo().log_error(
                    error_message=f"MCPObjectController: "
                    f"Unsupported method {xmlrpc_method}. "
                    f"Only execute_kw is allowed.",
                    error_code="E400",
                    endpoint="/mcp/xmlrpc/object",
                    operation=xmlrpc_method,
                    ip_address=_get_client_ip(),
                )
            raise xmlrpclib.Fault(
                XMLRPC_FAULT_CODES["bad_request"],
                f"MCPObjectController: Unsupported method "
                f"{xmlrpc_method}. Only execute_kw is allowed.",
            )

        if len(params) < 5:
            raise xmlrpclib.Fault(
                XMLRPC_FAULT_CODES["bad_request"],
                "MCPObjectController: Insufficient parameters for execute_kw.",
            )

    def _identify_user(
        self, auth_token: Any, uid: Any
    ) -> Tuple[Optional[Any], Optional[int]]:
        """
        Identify user from API key or uid for rate limiting.

        :param auth_token: The authentication token (password or API key)
        :param uid: The user ID from params
        :return: Tuple of (user_obj, user_id)
        """
        user_obj = None
        user_id = None

        # First try to get user from API key if it looks like one
        if isinstance(auth_token, str) and len(auth_token) > 20:
            user_obj = auth.get_user_from_api_key(auth_token)
            if user_obj:
                user_id = user_obj.id
                _logger.debug(
                    f"MCP XML-RPC: Identified user {user_id} "
                    f"from API key for rate limiting."
                )

        # If no user from API key and uid is provided, use uid for rate limiting
        if not user_id and uid:
            user_id = uid

        return user_obj, user_id

    def _apply_rate_limiting(
        self,
        user_obj: Optional[Any],
        user_id: Optional[int],
        model_name: str,
        model_method: str,
    ) -> None:
        """
        Apply rate limiting if enabled.

        :param user_obj: The user object (if identified from API key)
        :param user_id: The user ID for rate limiting
        :param model_name: The model being accessed
        :param model_method: The method being called
        :raises xmlrpclib.Fault: If rate limit exceeded
        """
        is_enabled = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mcp_server.enable_rate_limiting", "True")
            == "True"
        )
        if not is_enabled:
            return

        # Handle authenticated users
        if user_id:
            if not check_rate_limit(user_id):
                _logger.warning(
                    f"MCP XML-RPC: Rate limit exceeded for user ID "
                    f"{user_id} on {model_name}.{model_method}."
                )
                env_for_log = request.env(user=user_obj.id) if user_obj else request.env
                env_for_log["mcp.log"].sudo().log_rate_limit_exceeded(
                    user_id=user_id,
                    endpoint="/mcp/xmlrpc/object",
                    ip_address=_get_client_ip(),
                )
                raise xmlrpclib.Fault(
                    XMLRPC_FAULT_CODES["rate_limit"],
                    "Too many requests. Rate limit exceeded.",
                )
            record_api_request(user_id)
        else:
            anonymous_id = -1
            if not check_rate_limit(anonymous_id):
                raise xmlrpclib.Fault(
                    XMLRPC_FAULT_CODES["rate_limit"],
                    "Too many requests. Rate limit exceeded.",
                )
            record_api_request(anonymous_id)

    def _get_env_for_user(self, user_obj: Optional[Any], uid: Any) -> Any:
        """
        Get environment for the appropriate user context.

        :param user_obj: The user object (if identified from API key)
        :param uid: The user ID from params
        :return: Odoo environment for the user
        """
        if user_obj:
            return request.env(user=user_obj.id)

        if uid:
            try:
                return request.env(user=uid)
            except Exception as e:
                # Log the failure but continue with default environment
                _logger.debug(f"Failed to create environment for uid {uid}: {e}")

        return request.env

    def _extract_record_ids(self, params: list) -> Optional[list]:
        """
        Extract record IDs from params if available.

        :param params: The XML-RPC parameters
        :return: List of record IDs or None
        """
        if len(params) > 5 and isinstance(params[5], list):
            # For methods like read, write that have record IDs in params[5]
            if params[5] and isinstance(params[5][0], int):
                return params[5]
        return None

    def _mcp_object_dispatch(self, xmlrpc_method: str, params: list):
        """
        Dispatch XML-RPC object calls with MCP access control.

        :param xmlrpc_method: The XML-RPC method name
        :type xmlrpc_method: str
        :param params: The XML-RPC parameters
        :type params: list
        :return: The result from Odoo's model service
        :raises xmlrpclib.Fault: If access is denied or parameters are invalid
        """
        self._validate_request(xmlrpc_method, params)

        # Standard params for execute_kw: (db_name, uid, password, model_name,
        # model_method, args_array, kwargs_dict)
        uid = params[1]
        auth_token = params[2]
        model_method = params[4]

        # Validate model name
        try:
            model_name = utils.sanitize_model_name(params[3])
        except ValueError as e:
            raise xmlrpclib.Fault(
                XMLRPC_FAULT_CODES["bad_request"], f"Invalid model name: {e}"
            ) from e

        # Identify user for rate limiting
        user_obj, user_id = self._identify_user(auth_token, uid)

        # Apply rate limiting if enabled
        self._apply_rate_limiting(user_obj, user_id, model_name, model_method)

        # Create environment for MCP access check
        env_for_check = self._get_env_for_user(user_obj, uid)

        # Track start time for performance logging
        start_time = datetime.now()
        ip_address = _get_client_ip()

        # MCP Access Checks
        if not utils.check_mcp_access(env_for_check, model_name, model_method):
            env_for_check["mcp.log"].sudo().log_permission_denied(
                model_name=model_name,
                operation=model_method,
                user_id=user_id,
                endpoint="/mcp/xmlrpc/object",
                ip_address=ip_address,
                error_message=f"Access denied by MCP for model "
                f"'{model_name}' method '{model_method}'.",
            )
            raise xmlrpclib.Fault(
                XMLRPC_FAULT_CODES["forbidden"],
                f"Access denied by MCP for model "
                f"'{model_name}' method '{model_method}'.",
            )

        # If all checks pass, dispatch to Odoo's standard model service
        _logger.info(
            f"MCP XML-RPC: Access GRANTED for {model_name}.{model_method} "
            f"(User ID: {user_id if user_id else 'N/A'})"
        )

        try:
            result = model_service_root.dispatch(xmlrpc_method, params)

            # Log successful model access
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            env_for_check["mcp.log"].sudo().log_model_access(
                model_name=model_name,
                operation=model_method,
                user_id=user_id,
                record_ids=self._extract_record_ids(params),
                endpoint="/mcp/xmlrpc/object",
                http_method="POST",
                duration_ms=duration_ms,
                ip_address=ip_address,
            )

            return result
        except Exception as e:
            # Log error
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            env_for_check["mcp.log"].sudo().log_error(
                error_message=str(e),
                error_code="E500",
                endpoint="/mcp/xmlrpc/object",
                model_name=model_name,
                operation=model_method,
                user_id=user_id,
                ip_address=ip_address,
            )
            raise

    @http.route(
        "/mcp/xmlrpc/object", type="http", auth="none", methods=["POST"], csrf=False
    )
    def index(self, **kwargs):
        # Check if MCP is globally enabled
        if not utils.is_mcp_enabled():
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["forbidden"],
                "MCP Server is disabled globally.",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])

        data = request.httprequest.data
        try:
            params, method = xmlrpclib.loads(data)
            result = self._mcp_object_dispatch(method, params)
            # Use Odoo's custom XML-RPC marshaller that handles date objects
            response_data = odoo_dumps((result,))
            return request.make_response(response_data, [("Content-Type", "text/xml")])
        except xmlrpclib.Fault as e:
            _logger.warning(
                f"MCPObjectController XML-RPC Fault: "
                f"Code {e.faultCode}, String: {e.faultString}"
            )
            return request.make_response(
                xmlrpclib.dumps(e, methodresponse=1, allow_none=1),
                [("Content-Type", "text/xml")],
            )
        except Exception as e:
            error_msg = str(e)
            _logger.error(
                "Critical error in MCPObjectController dispatch: %s",
                error_msg,
                exc_info=True,
            )
            fault_response = _generate_xmlrpc_fault(
                XMLRPC_FAULT_CODES["internal_error"],
                f"Internal Server Error in MCPObjectController: {error_msg}",
            )
            return request.make_response(fault_response, [("Content-Type", "text/xml")])
