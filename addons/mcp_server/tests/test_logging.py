"""Tests for MCP logging functionality."""

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .test_helpers import create_test_user


@tagged("much_unit", "post_install", "-at_install")
class TestMCPLogging(TransactionCase):
    def setUp(self):
        super().setUp()
        # Enable MCP logging in test context
        self.MCPLog = self.env["mcp.log"].with_context(test_mcp_logging=True)
        self.test_user = create_test_user(
            self.env, "Test MCP User", "test_mcp_user", email="test_mcp@example.com"
        )
        # Enable logging
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.enable_logging", "True"
        )

    def test_log_event_basic(self):
        """Test basic log event creation."""
        log = self.MCPLog.log_event(
            "auth_success",
            user_id=self.test_user.id,
            ip_address="192.168.1.1",
            endpoint="/mcp/auth/validate",
        )

        self.assertTrue(log)
        self.assertEqual(log.event_type, "auth_success")
        self.assertEqual(log.user_id.id, self.test_user.id)
        self.assertEqual(log.ip_address, "192.168.1.1")
        self.assertEqual(log.endpoint, "/mcp/auth/validate")

    def test_log_authentication_success(self):
        """Test authentication success logging."""
        log = self.MCPLog.log_authentication(
            success=True,
            user_id=self.test_user.id,
            api_key_used=True,
            ip_address="10.0.0.1",
        )

        self.assertEqual(log.event_type, "auth_success")
        self.assertEqual(log.user_id.id, self.test_user.id)
        self.assertTrue(log.api_key_used)
        self.assertEqual(log.ip_address, "10.0.0.1")

    def test_log_authentication_failure(self):
        """Test authentication failure logging."""
        log = self.MCPLog.log_authentication(
            success=False,
            user_id=None,
            api_key_used=True,
            ip_address="10.0.0.2",
            error_message="Invalid API key",
        )

        self.assertEqual(log.event_type, "auth_failure")
        self.assertFalse(log.user_id)
        self.assertTrue(log.api_key_used)
        self.assertEqual(log.error_message, "Invalid API key")

    def test_log_model_access(self):
        """Test model access logging."""
        log = self.MCPLog.log_model_access(
            model_name="res.partner",
            operation="search",
            user_id=self.test_user.id,
            record_ids=[1, 2, 3],
            endpoint="/mcp/xmlrpc/object",
            http_method="POST",
            duration_ms=125,
            ip_address="192.168.1.100",
        )

        self.assertEqual(log.event_type, "model_access")
        self.assertEqual(log.model_name, "res.partner")
        self.assertEqual(log.operation, "search")
        self.assertEqual(log.record_ids, "1,2,3")
        self.assertEqual(log.duration_ms, 125)

    def test_log_error(self):
        """Test error logging."""
        log = self.MCPLog.log_error(
            error_message="Model not found",
            error_code="E404",
            endpoint="/mcp/models/invalid.model/access",
            model_name="invalid.model",
            operation="access",
            user_id=self.test_user.id,
            ip_address="192.168.1.50",
        )

        self.assertEqual(log.event_type, "error")
        self.assertEqual(log.error_message, "Model not found")
        self.assertEqual(log.error_code, "E404")
        self.assertEqual(log.model_name, "invalid.model")

    def test_log_rate_limit_exceeded(self):
        """Test rate limit exceeded logging."""
        log = self.MCPLog.log_rate_limit_exceeded(
            user_id=self.test_user.id, endpoint="/mcp/models", ip_address="192.168.1.75"
        )

        self.assertEqual(log.event_type, "rate_limit")
        self.assertEqual(log.user_id.id, self.test_user.id)
        self.assertEqual(log.error_message, "Rate limit exceeded")

    def test_log_permission_denied(self):
        """Test permission denied logging."""
        log = self.MCPLog.log_permission_denied(
            model_name="account.move",
            operation="create",
            user_id=self.test_user.id,
            endpoint="/mcp/xmlrpc/object",
            ip_address="192.168.1.90",
        )

        self.assertEqual(log.event_type, "permission_denied")
        self.assertEqual(log.model_name, "account.move")
        self.assertEqual(log.operation, "create")
        self.assertIn("Permission denied", log.error_message)

    def test_logging_disabled(self):
        """Test that logging is skipped when disabled."""
        # Disable logging
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.enable_logging", "False"
        )

        log = self.MCPLog.log_event(
            "auth_success", user_id=self.test_user.id, ip_address="192.168.1.1"
        )

        # Should return empty recordset
        self.assertFalse(log)

    def test_data_truncation(self):
        """Test that large data fields are truncated."""
        large_data = "x" * 15000  # Larger than max_text_length (10000)

        log = self.MCPLog.log_event(
            "error",
            error_message=large_data,
            request_data=large_data,
            response_data=large_data,
            user_agent=large_data,
        )

        self.assertTrue(log.error_message.endswith("... [truncated]"))
        self.assertTrue(log.request_data.endswith("... [truncated]"))
        self.assertTrue(log.response_data.endswith("... [truncated]"))
        self.assertTrue(log.user_agent.endswith("... [truncated]"))
        self.assertLessEqual(len(log.error_message), 10020)  # 10000 + '... [truncated]'

    def test_cleanup_old_logs(self):
        """Test cleanup of old log entries."""
        # Create logs with different ages
        now = datetime.now()

        # Create old log (35 days ago)
        old_log = self.MCPLog.create(
            {"event_type": "auth_success", "create_date": now - timedelta(days=35)}
        )

        # Create recent log (5 days ago)
        recent_log = self.MCPLog.create(
            {"event_type": "auth_success", "create_date": now - timedelta(days=5)}
        )

        # Create today's log
        today_log = self.MCPLog.create(
            {"event_type": "auth_success", "create_date": now}
        )

        # Clean up logs older than 30 days
        deleted_count = self.MCPLog.cleanup_old_logs(days=30)

        self.assertEqual(deleted_count, 1)
        self.assertFalse(old_log.exists())
        self.assertTrue(recent_log.exists())
        self.assertTrue(today_log.exists())

    def test_cleanup_with_zero_retention(self):
        """Test that cleanup does nothing when retention is 0."""
        # Create a log
        log = self.MCPLog.create(
            {
                "event_type": "auth_success",
                "create_date": datetime.now() - timedelta(days=100),
            }
        )

        # Set retention to 0 (keep forever)
        deleted_count = self.MCPLog.cleanup_old_logs(days=0)

        self.assertEqual(deleted_count, 0)
        self.assertTrue(log.exists())

    def test_cleanup_with_config_parameter(self):
        """Test cleanup using config parameter for retention days."""
        # Set retention to 7 days in config
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.log_retention_days", "7"
        )

        # Create logs
        old_log = self.MCPLog.create(
            {
                "event_type": "auth_success",
                "create_date": datetime.now() - timedelta(days=10),
            }
        )
        recent_log = self.MCPLog.create(
            {
                "event_type": "auth_success",
                "create_date": datetime.now() - timedelta(days=3),
            }
        )

        # Clean up using config parameter
        deleted_count = self.MCPLog.cleanup_old_logs()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(old_log.exists())
        self.assertTrue(recent_log.exists())

    def test_get_summary(self):
        """Test log summary generation."""
        log = self.MCPLog.create(
            {
                "event_type": "model_access",
                "model_name": "res.partner",
                "operation": "search",
                "error_message": "This is a very long error message "
                "that should be truncated in the summary display",
            }
        )

        summary = log.get_summary()
        self.assertIn("model_access", summary)
        self.assertIn("res.partner", summary)
        self.assertIn("search", summary)
        self.assertIn("...", summary)  # Error message should be truncated

    def test_display_name_computation(self):
        """Test display name computation."""
        log = self.MCPLog.create(
            {
                "event_type": "model_access",
                "model_name": "res.partner",
                "operation": "create",
            }
        )

        # Force computation
        log._compute_display_name()

        self.assertIn("Model Access", log.display_name)
        self.assertIn("res.partner", log.display_name)
        self.assertIn("create", log.display_name)

    def test_log_creation_error_handling(self):
        """Test that log creation errors are handled gracefully."""
        with patch.object(
            self.MCPLog, "create", side_effect=Exception("Database error")
        ):
            # Should not raise exception, just return empty recordset
            log = self.MCPLog.log_event("auth_success", user_id=self.test_user.id)
            self.assertFalse(log)

    def test_ipv6_address_storage(self):
        """Test that IPv6 addresses can be stored."""
        ipv6_address = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        log = self.MCPLog.log_event("auth_success", ip_address=ipv6_address)

        self.assertEqual(log.ip_address, ipv6_address)

    def test_json_data_fields(self):
        """Test storing JSON data in request/response fields."""
        request_data = (
            '{"method": "search", "params": {"domain": [["active", "=", true]]}}'
        )
        response_data = '{"result": [1, 2, 3], "count": 3}'

        log = self.MCPLog.log_event(
            "model_access", request_data=request_data, response_data=response_data
        )

        self.assertEqual(log.request_data, request_data)
        self.assertEqual(log.response_data, response_data)
