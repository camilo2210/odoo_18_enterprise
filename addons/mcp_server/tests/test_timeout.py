import time
from unittest.mock import MagicMock, patch

from odoo.tests import common, tagged

from ..controllers import rate_limiting


@tagged("much_unit", "post_install", "-at_install")
class TestRequestTimeout(common.TransactionCase):
    """Test request timeout functionality"""

    def setUp(self):
        super().setUp()
        # Set default timeout configuration
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_timeout", "2"
        )  # 2 seconds for testing

    def test_request_timeout_decorator_success(self):
        """Test that request completes successfully within timeout"""

        @rate_limiting.request_timeout
        def fast_endpoint():
            # Simulate a fast operation
            time.sleep(0.1)
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = fast_endpoint()
            self.assertEqual(result, {"success": True})

    def test_request_timeout_decorator_timeout(self):
        """Test that request times out when exceeding limit"""

        @rate_limiting.request_timeout
        def slow_endpoint():
            # Simulate a slow operation that exceeds timeout
            time.sleep(3)  # Longer than our 2 second timeout
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        # Mock response_utils to check timeout response
        mock_response_utils = MagicMock()
        mock_response_utils.error_response.return_value = {"error": "timeout"}

        with (
            patch(
                "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
            ),
            patch(
                "odoo.addons.mcp_server.controllers.rate_limiting.response_utils",
                mock_response_utils,
            ),
        ):
            # Only test on Unix-like systems where signal.SIGALRM is available
            if hasattr(rate_limiting.signal, "SIGALRM"):
                result = slow_endpoint()
                # Check that error response was called with timeout error
                mock_response_utils.error_response.assert_called_once()
                call_args = mock_response_utils.error_response.call_args
                self.assertIn("exceeded timeout limit", call_args[0][0])
                self.assertEqual(call_args[0][1], "E408")
                self.assertEqual(call_args[1]["status"], 408)
            else:
                # On non-Unix systems, function should complete normally
                result = slow_endpoint()
                self.assertEqual(result, {"success": True})

    def test_request_timeout_disabled_with_zero(self):
        """Test that timeout is disabled when set to 0"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_timeout", "0"
        )

        @rate_limiting.request_timeout
        def slow_endpoint():
            # This would timeout if timeout was enabled
            time.sleep(1)
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = slow_endpoint()
            self.assertEqual(result, {"success": True})

    def test_request_timeout_disabled_with_negative(self):
        """Test that timeout is disabled when set to negative value"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_timeout", "-5"
        )

        @rate_limiting.request_timeout
        def slow_endpoint():
            # This would timeout if timeout was enabled
            time.sleep(1)
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = slow_endpoint()
            self.assertEqual(result, {"success": True})

    def test_request_timeout_invalid_value(self):
        """Test handling of invalid timeout value"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_timeout", "invalid"
        )

        @rate_limiting.request_timeout
        def endpoint():
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            # Should use default timeout (30 seconds) but still work
            result = endpoint()
            self.assertEqual(result, {"success": True})
