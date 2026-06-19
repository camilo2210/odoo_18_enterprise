"""Tests for MCP Server authentication."""

import json
from datetime import datetime, timedelta

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from .test_helpers import create_test_user


@tagged("much_unit", "post_install", "-at_install")
class TestMCPAuthentication(HttpCase):
    """Test MCP Server authentication functionality."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test user with API key
        cls.test_user = create_test_user(
            cls.env,
            "Test MCP User",
            "test_mcp_user",  # nosec
            password="test_password",
            groups_id=[(6, 0, [cls.env.ref("mcp_server.group_mcp_user").id])],
        )

        # Create API key for test user
        env_as_user = cls.env(user=cls.test_user)
        cls.api_key = env_as_user["res.users.apikeys"]._generate(
            "rpc", "Test API Key", datetime.now() + timedelta(days=30)
        )

    def test_01_auth_with_valid_api_key(self):
        """Test authentication with valid API key."""
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["valid"])
        self.assertEqual(data["data"]["user_id"], self.test_user.id)
        self.assertEqual(data["data"]["auth_method"], "api_key")

    def test_02_auth_with_invalid_api_key(self):
        """Test authentication with invalid API key."""
        headers = {
            "X-API-Key": "invalid_api_key_12345",
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")

    def test_03_auth_with_no_api_key(self):
        """Test authentication with no API key header."""
        headers = {
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")

    def test_04_auth_with_empty_api_key(self):
        """Test authentication with empty API key header."""
        headers = {
            "X-API-Key": "",
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/auth/validate", headers=headers)
        self.assertEqual(response.status_code, 401)

        data = json.loads(response.text)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "E401")

    def test_05_system_info_requires_auth(self):
        """Test that system info endpoint requires authentication."""
        # No API key
        response = self.url_open(
            "/mcp/system/info", headers={"Accept": "application/json"}
        )
        self.assertEqual(response.status_code, 401)

        # With valid API key
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/system/info", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertIn("db_name", data["data"])
        self.assertIn("odoo_version", data["data"])

    def test_06_models_endpoint_requires_auth(self):
        """Test that models endpoint requires authentication."""
        # No API key
        response = self.url_open("/mcp/models", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 401)

        # With valid API key
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }
        response = self.url_open("/mcp/models", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertIn("models", data["data"])
        self.assertIsInstance(data["data"]["models"], list)


@tagged("much_unit", "post_install", "-at_install")
class TestSessionAuth(HttpCase):
    """Test session-based authentication for MCP REST endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_user = create_test_user(
            cls.env,
            "Test Session User",
            "test_session_user",
            password="test_session_pass",
            groups_id=[(6, 0, [cls.env.ref("mcp_server.group_mcp_user").id])],
        )

        # Create API key for priority test
        env_as_user = cls.env(user=cls.test_user)
        cls.api_key = env_as_user["res.users.apikeys"]._generate(
            "rpc", "Test Session API Key", datetime.now() + timedelta(days=30)
        )

    def test_01_session_auth_on_models_endpoint(self):
        """Session-authenticated user can access /mcp/models."""
        self.authenticate("test_session_user", "test_session_pass")
        response = self.url_open("/mcp/models", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertTrue(data["success"])

    def test_02_session_auth_on_validate_endpoint(self):
        """Session-authenticated user can validate auth."""
        self.authenticate("test_session_user", "test_session_pass")
        response = self.url_open(
            "/mcp/auth/validate", headers={"Accept": "application/json"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_id"], self.test_user.id)
        self.assertEqual(data["data"]["auth_method"], "session")

    def test_03_session_auth_on_system_info(self):
        """Session-authenticated user can access /mcp/system/info."""
        self.authenticate("test_session_user", "test_session_pass")
        response = self.url_open(
            "/mcp/system/info", headers={"Accept": "application/json"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertTrue(data["success"])

    def test_04_no_auth_returns_401(self):
        """Request without API key or session returns 401."""
        response = self.url_open("/mcp/models", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 401)

    def test_05_api_key_takes_priority(self):
        """When both API key and session present, API key is used."""
        self.authenticate("test_session_user", "test_session_pass")
        response = self.url_open(
            "/mcp/auth/validate",
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(data["data"]["auth_method"], "api_key")
