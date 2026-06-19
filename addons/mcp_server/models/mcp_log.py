"""MCP Log Model for tracking MCP server activity."""

import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MCPLog(models.Model):
    _name = "mcp.log"
    _description = "MCP Server Activity Log"
    _order = "create_date desc"
    _rec_name = "event_type"

    # Basic fields
    event_type = fields.Selection(
        [
            ("auth_success", "Authentication Success"),
            ("auth_failure", "Authentication Failure"),
            ("model_access", "Model Access"),
            ("resource_retrieval", "Resource Retrieval"),
            ("write_operation", "Write Operation"),
            ("error", "Error"),
            ("rate_limit", "Rate Limit Exceeded"),
            ("permission_denied", "Permission Denied"),
        ],
        required=True,
        index=True,
    )

    # User and authentication info
    user_id = fields.Many2one("res.users", string="User", index=True)
    api_key_used = fields.Boolean(string="API Key Used", default=False)
    ip_address = fields.Char(string="IP Address", size=45)  # Size 45 for IPv6

    # Request details
    endpoint = fields.Char(index=True)
    http_method = fields.Char()
    model_name = fields.Char(string="Model", index=True)
    operation = fields.Char()
    record_ids = fields.Char(string="Record IDs")

    # Request and response data
    request_data = fields.Text()
    response_data = fields.Text()

    # Error details
    error_message = fields.Text()
    error_code = fields.Char()

    # Performance metrics
    duration_ms = fields.Integer(string="Duration (ms)")

    # Additional metadata
    session_id = fields.Char(string="Session ID")
    user_agent = fields.Text()

    @api.model
    def log_event(self, event_type, **kwargs):
        """
        Create a log entry for an MCP event.

        :param event_type: Type of event from the selection
        :param kwargs: Additional data for the log entry
        :return: Created log record
        """
        # Skip logging if MCP logging is disabled
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mcp_server.enable_logging", "True")
            != "True"
        ):
            return self.env["mcp.log"]

        # Skip logging only if explicitly requested via context
        # This allows tests to control when logging should be skipped
        if self.env.context.get("skip_mcp_logging"):
            return self.env["mcp.log"]

        # Detect test mode properly:
        # 1. Check if we're in actual test mode (not just dev mode)
        # 2. test_cr is set when running with --test-enable
        # 3. Skip logging in test mode UNLESS we're specifically testing logging
        in_test_mode = (
            hasattr(self.env.registry, "test_cr")
            and self.env.registry.test_cr is not None
        )

        if in_test_mode and not self.env.context.get("test_mcp_logging"):
            # We're in test mode and not specifically testing logging
            return self.env["mcp.log"]

        # Prepare log data
        log_data = {
            "event_type": event_type,
            "user_id": kwargs.get(
                "user_id", self.env.user.id if self.env.user.id != 1 else False
            ),
            "api_key_used": kwargs.get("api_key_used", False),
            "ip_address": kwargs.get("ip_address"),
            "endpoint": kwargs.get("endpoint"),
            "http_method": kwargs.get("http_method"),
            "model_name": kwargs.get("model_name"),
            "operation": kwargs.get("operation"),
            "record_ids": kwargs.get("record_ids"),
            "request_data": kwargs.get("request_data"),
            "response_data": kwargs.get("response_data"),
            "error_message": kwargs.get("error_message"),
            "error_code": kwargs.get("error_code"),
            "duration_ms": kwargs.get("duration_ms"),
            "session_id": kwargs.get("session_id"),
            "user_agent": kwargs.get("user_agent"),
        }

        # Truncate large data fields to prevent database issues
        max_text_length = 10000
        for field in ["request_data", "response_data", "error_message", "user_agent"]:
            if log_data.get(field) and len(str(log_data[field])) > max_text_length:
                log_data[field] = (
                    str(log_data[field])[:max_text_length] + "... [truncated]"
                )

        try:
            # Create log entry with sudo to ensure it's always created
            return self.sudo().create(log_data)
        except Exception as e:
            # In test mode, this is expected - don't spam the logs
            in_test_mode = (
                hasattr(self.env.registry, "test_cr")
                and self.env.registry.test_cr is not None
            )
            if not in_test_mode:
                _logger.error(f"Failed to create MCP log entry: {e}")
            return self.env["mcp.log"]

    @api.model
    def log_authentication(
        self,
        success,
        user_id=None,
        api_key_used=False,
        ip_address=None,
        error_message=None,
    ):
        """Log authentication attempts."""
        return self.log_event(
            "auth_success" if success else "auth_failure",
            user_id=user_id,
            api_key_used=api_key_used,
            ip_address=ip_address,
            error_message=error_message,
        )

    @api.model
    def log_model_access(
        self,
        model_name,
        operation,
        user_id=None,
        record_ids=None,
        endpoint=None,
        http_method=None,
        duration_ms=None,
        ip_address=None,
    ):
        """Log model access operations."""
        record_ids_str = ",".join(map(str, record_ids)) if record_ids else None
        return self.log_event(
            "model_access",
            model_name=model_name,
            operation=operation,
            user_id=user_id,
            record_ids=record_ids_str,
            endpoint=endpoint,
            http_method=http_method,
            duration_ms=duration_ms,
            ip_address=ip_address,
        )

    @api.model
    def log_error(
        self,
        error_message,
        error_code=None,
        endpoint=None,
        model_name=None,
        operation=None,
        user_id=None,
        ip_address=None,
        request_data=None,
    ):
        """Log error events."""
        return self.log_event(
            "error",
            error_message=error_message,
            error_code=error_code,
            endpoint=endpoint,
            model_name=model_name,
            operation=operation,
            user_id=user_id,
            ip_address=ip_address,
            request_data=request_data,
        )

    @api.model
    def log_rate_limit_exceeded(self, user_id, endpoint=None, ip_address=None):
        """Log rate limit exceeded events."""
        return self.log_event(
            "rate_limit",
            user_id=user_id,
            endpoint=endpoint,
            ip_address=ip_address,
            error_message="Rate limit exceeded",
        )

    @api.model
    def log_permission_denied(
        self,
        model_name,
        operation,
        user_id=None,
        endpoint=None,
        ip_address=None,
        error_message=None,
    ):
        """Log permission denied events."""
        return self.log_event(
            "permission_denied",
            model_name=model_name,
            operation=operation,
            user_id=user_id,
            endpoint=endpoint,
            ip_address=ip_address,
            error_message=error_message
            or f"Permission denied for {operation} on {model_name}",
        )

    @api.model
    def cleanup_old_logs(self, days=None):
        """
        Clean up old log entries based on retention settings.

        :param days: Number of days to retain logs (overrides config if provided)
        :return: Number of deleted records
        """
        if days is None:
            # Get retention days from config, default to 30
            days = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mcp_server.log_retention_days", "30")
            )

        if days <= 0:
            # 0 or negative means keep logs forever
            return 0

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)

        # Find and delete old logs
        old_logs = self.search([("create_date", "<", cutoff_date)])
        count = len(old_logs)
        old_logs.unlink()

        _logger.info(f"Cleaned up {count} MCP log entries older than {days} days")
        return count

    @api.model
    def _register_hook(self):
        """Register cleanup cron job on module installation."""
        super()._register_hook()
        # Create or update the cron job for log cleanup
        cron_vals = {
            "name": "MCP Log Cleanup",
            "model_id": self.env["ir.model"].search([("model", "=", "mcp.log")]).id,
            "state": "code",
            "code": "model.cleanup_old_logs()",
            "interval_type": "days",
            "interval_number": 1,
            # 'numbercall': -1,  # This field doesn't exist in Odoo 18
            "active": True,
        }
        cron = self.env["ir.cron"].search([("name", "=", "MCP Log Cleanup")])
        if cron:
            cron.write(cron_vals)
        else:
            self.env["ir.cron"].create(cron_vals)

    def get_summary(self):
        """Get a summary of the log entry for display."""
        self.ensure_one()
        summary = f"{self.event_type}"
        if self.model_name:
            summary += f" - {self.model_name}"
        if self.operation:
            summary += f".{self.operation}"
        if self.error_message:
            summary += f" - {self.error_message[:50]}..."
        return summary

    @api.depends("event_type", "model_name", "operation")
    def _compute_display_name(self):
        """Compute display name for tree views."""
        for record in self:
            parts = [
                dict(record._fields["event_type"].selection).get(record.event_type, "")
            ]
            if record.model_name:
                parts.append(record.model_name)
            if record.operation:
                parts.append(record.operation)
            record.display_name = " - ".join(filter(None, parts))
