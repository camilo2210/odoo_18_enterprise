from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from odoo.tests import common, tagged
from odoo.tools import mute_logger

from ..controllers import rate_limiting
from .test_helpers import create_test_user


@tagged("much_unit", "post_install", "-at_install")
class TestRateLimiting(common.TransactionCase):
    """Test rate limiting functionality"""

    def setUp(self):
        super().setUp()
        # Clear the rate limiting cache before each test
        rate_limiting._api_request_cache.clear()

        # Create test user
        self.test_user = create_test_user(
            self.env,
            "Rate Limit Test User",
            "rate_limit_test_user",
            email="rate_limit_test@example.com",
        )

        # Set default rate limiting configuration
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "300"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.enable_rate_limiting", "True"
        )

    def test_get_request_limit_default(self):
        """Test getting default request limit"""
        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            limit = rate_limiting.get_request_limit()
            self.assertEqual(limit, 300)

    def test_get_request_limit_custom(self):
        """Test getting custom request limit"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "100"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            limit = rate_limiting.get_request_limit()
            self.assertEqual(limit, 100)

    def test_get_request_limit_unlimited(self):
        """Test getting unlimited request limit (0)"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "0"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            limit = rate_limiting.get_request_limit()
            self.assertEqual(limit, 0)  # Should return 0 for unlimited

    def test_get_request_limit_minimum_enforced(self):
        """Test that minimum request limit is enforced"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "5"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            limit = rate_limiting.get_request_limit()
            self.assertEqual(limit, rate_limiting.MINIMUM_REQUEST_LIMIT)  # Should be 10

    @mute_logger("odoo.addons.mcp_server.controllers.rate_limiting")
    def test_get_request_limit_invalid_value(self):
        """Test handling of invalid request limit value"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "invalid"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            limit = rate_limiting.get_request_limit()
            self.assertEqual(
                limit, rate_limiting.DEFAULT_REQUEST_LIMIT
            )  # Should fallback to 300

    def test_record_api_request(self):
        """Test recording API requests"""
        user_id = self.test_user.id

        # Record a request
        rate_limiting.record_api_request(user_id)

        # Check that request was recorded
        self.assertIn(user_id, rate_limiting._api_request_cache)
        self.assertEqual(len(rate_limiting._api_request_cache[user_id]), 1)

    def test_record_api_request_multiple(self):
        """Test recording multiple API requests"""
        user_id = self.test_user.id

        # Record multiple requests
        for _ in range(3):
            rate_limiting.record_api_request(user_id)

        # Check that all requests were recorded
        self.assertEqual(len(rate_limiting._api_request_cache[user_id]), 3)

    def test_record_api_request_cleanup_old(self):
        """Test cleanup of old timestamps"""
        user_id = self.test_user.id

        # Add an old timestamp manually
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        rate_limiting._api_request_cache[user_id] = [old_time]

        # Record a new request (should clean up old one)
        rate_limiting.record_api_request(user_id)

        # Should only have the new request
        self.assertEqual(len(rate_limiting._api_request_cache[user_id]), 1)

    def test_check_rate_limit_no_requests(self):
        """Test rate limit check with no previous requests"""
        user_id = self.test_user.id

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = rate_limiting.check_rate_limit(user_id)
            self.assertTrue(result)  # Should be within limit

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within limit"""
        user_id = self.test_user.id

        # Record a few requests (well under limit)
        for _ in range(5):
            rate_limiting.record_api_request(user_id)

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = rate_limiting.check_rate_limit(user_id)
            self.assertTrue(result)  # Should be within limit

    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit is exceeded"""
        user_id = self.test_user.id

        # Set a limit just above minimum (10) for testing
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "12"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            # Record requests exceeding the limit of 12
            for _ in range(13):  # More than the limit of 12
                rate_limiting.record_api_request(user_id)

            result = rate_limiting.check_rate_limit(user_id)
            self.assertFalse(result)  # Should exceed limit

    def test_check_rate_limit_old_requests_ignored(self):
        """Test that old requests don't count towards limit"""
        user_id = self.test_user.id

        # Set a limit above minimum (10) for testing
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "12"
        )

        # Add old timestamps that should be ignored
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        rate_limiting._api_request_cache[user_id] = [
            old_time
        ] * 15  # More than limit but old

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = rate_limiting.check_rate_limit(user_id)
            self.assertTrue(result)  # Should be within limit (old requests ignored)

    def test_check_rate_limit_unlimited(self):
        """Test rate limit check with unlimited setting (0)"""
        user_id = self.test_user.id

        # Set unlimited (0)
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "0"
        )

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            # Record many requests
            for _ in range(1000):  # Way more than any reasonable limit
                rate_limiting.record_api_request(user_id)

            result = rate_limiting.check_rate_limit(user_id)
            self.assertTrue(result)  # Should always pass with unlimited

    def test_rate_limit_decorator_enabled_within_limit(self):
        """Test rate limit decorator when enabled and within limit"""

        @rate_limiting.rate_limit
        def test_endpoint(user=None):
            return {"success": True, "user_id": user.id if user else None}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = test_endpoint(user=self.test_user)
            self.assertEqual(result["success"], True)
            self.assertEqual(result["user_id"], self.test_user.id)

    def test_rate_limit_decorator_disabled(self):
        """Test rate limit decorator when disabled"""
        # Disable rate limiting
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.enable_rate_limiting", "False"
        )

        @rate_limiting.rate_limit
        def test_endpoint(user=None):
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = test_endpoint(user=self.test_user)
            self.assertEqual(result["success"], True)

    def test_rate_limit_decorator_exceeded(self):
        """Test rate limit decorator when limit is exceeded"""
        # Set a limit above minimum (10) for testing
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "11"
        )

        @rate_limiting.rate_limit
        def test_endpoint(user=None):
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        # Mock the error response to avoid request object issues
        mock_error_response = {"error": "Too many requests", "code": "E429"}

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            with patch(
                "odoo.addons.mcp_server.controllers.response_utils.error_response",
                return_value=mock_error_response,
            ):
                # Fill the cache to exceed limit of 11
                for _ in range(12):
                    rate_limiting.record_api_request(self.test_user.id)

                result = test_endpoint(user=self.test_user)
                self.assertEqual(result, mock_error_response)

    def test_rate_limit_decorator_no_user(self):
        """Test rate limit decorator without user (anonymous)"""

        @rate_limiting.rate_limit
        def test_endpoint(user=None):
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            result = test_endpoint()  # No user provided
            self.assertEqual(result["success"], True)

            # Check that anonymous request was recorded
            self.assertIn(
                -1, rate_limiting._api_request_cache
            )  # Anonymous user ID is -1

    def test_rate_limit_decorator_anonymous_exceeded(self):
        """Test rate limit decorator for anonymous user when limit exceeded"""
        # Set limit above minimum (10) for testing
        self.env["ir.config_parameter"].sudo().set_param(
            "mcp_server.request_limit", "11"
        )

        @rate_limiting.rate_limit
        def test_endpoint():
            return {"success": True}

        mock_request = MagicMock()
        mock_request.env = self.env

        # Mock the error response to avoid request object issues
        mock_error_response = {"error": "Too many anonymous requests", "code": "E429"}

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            with patch(
                "odoo.addons.mcp_server.controllers.response_utils.error_response",
                return_value=mock_error_response,
            ):
                # Fill anonymous cache to exceed limit of 11
                for _ in range(12):
                    rate_limiting.record_api_request(-1)  # Anonymous user ID

                result = test_endpoint()
                self.assertEqual(result, mock_error_response)

    def test_cache_persistence_across_calls(self):
        """Test that cache persists across multiple function calls"""
        user_id = self.test_user.id

        # Record requests in separate calls
        rate_limiting.record_api_request(user_id)
        rate_limiting.record_api_request(user_id)

        # Cache should contain both requests
        self.assertEqual(len(rate_limiting._api_request_cache[user_id]), 2)

        # Check rate limit should see both requests
        mock_request = MagicMock()
        mock_request.env = self.env

        with patch(
            "odoo.addons.mcp_server.controllers.rate_limiting.request", mock_request
        ):
            # Should still be within default limit of 300
            result = rate_limiting.check_rate_limit(user_id)
            self.assertTrue(result)
