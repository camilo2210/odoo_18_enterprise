from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from .test_helpers import create_test_config_settings


@tagged("much_unit", "post_install", "-at_install")
class TestConfigSettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Settings = self.env["res.config.settings"]

    def test_create_and_save_settings(self):
        """Test that settings can be created and saved."""
        settings = create_test_config_settings(
            self.env,
            mcp_enabled=True,
            mcp_request_limit=100,
            mcp_request_timeout=45,
            mcp_enable_logging=True,
            mcp_enable_rate_limiting=True,
        )

        # Execute the "save" onchange
        settings.execute()

        # Check that the values were saved to the system parameters
        param_obj = self.env["ir.config_parameter"].sudo()
        self.assertEqual(param_obj.get_param("mcp_server.enabled"), "True")
        self.assertEqual(param_obj.get_param("mcp_server.request_limit"), "100")
        self.assertEqual(param_obj.get_param("mcp_server.request_timeout"), "45")
        self.assertEqual(param_obj.get_param("mcp_server.enable_logging"), "True")
        self.assertEqual(param_obj.get_param("mcp_server.enable_rate_limiting"), "True")

    def test_default_values(self):
        """Test that default values are set correctly when not specified."""
        # Clear any existing parameters
        param_obj = self.env["ir.config_parameter"].sudo()
        params = [
            "mcp_server.enabled",
            "mcp_server.request_limit",
            "mcp_server.request_timeout",
            "mcp_server.enable_logging",
            "mcp_server.enable_rate_limiting",
        ]
        for param in params:
            param_obj.set_param(param, "")

        # Create new settings with defaults
        settings = create_test_config_settings(self.env)

        # Check default values
        self.assertFalse(settings.mcp_enabled)
        self.assertEqual(settings.mcp_request_limit, 300)
        self.assertEqual(settings.mcp_request_timeout, 30)
        self.assertTrue(settings.mcp_enable_logging)
        self.assertFalse(settings.mcp_enable_rate_limiting)

    def test_unlimited_rate_limit_setting(self):
        """Test that request limit can be set to 0 for unlimited."""
        settings = self.Settings.create(
            {
                "mcp_request_limit": 0,  # 0 means unlimited
                "mcp_enable_rate_limiting": True,
            }
        )

        # Execute the "save" onchange
        settings.execute()

        # Check that the value was saved correctly
        param_obj = self.env["ir.config_parameter"].sudo()
        self.assertEqual(param_obj.get_param("mcp_server.request_limit"), "0")

    def test_load_settings(self):
        """Test that settings are loaded from system parameters."""
        # Set some values in system parameters
        param_obj = self.env["ir.config_parameter"].sudo()
        param_obj.set_param("mcp_server.enabled", "False")
        param_obj.set_param("mcp_server.request_limit", "200")
        param_obj.set_param("mcp_server.request_timeout", "60")

        # Create settings and check they load from params
        settings = self.Settings.create({})

        # Check loaded values
        self.assertFalse(settings.mcp_enabled)
        self.assertEqual(settings.mcp_request_limit, 200)
        self.assertEqual(settings.mcp_request_timeout, 60)

    def test_settings_ui_display(self):
        """Test that settings UI view loads correctly."""
        # This test verifies the view can be loaded without errors
        view_id = self.env.ref("mcp_server.res_config_settings_view_form_mcp")
        self.assertTrue(view_id, "Settings view not found")

        # Try to load the view to check for errors
        settings = self.Settings.create({})
        view = settings.get_view(view_id.id, "form")
        self.assertTrue(view, "Failed to load settings view")
