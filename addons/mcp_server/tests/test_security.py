from odoo.exceptions import AccessError
from odoo.tests import common, tagged

from .test_helpers import create_test_user


@tagged("much_unit", "post_install", "-at_install")
class TestMcpSecurity(common.TransactionCase):
    def setUp(self):
        super().setUp()
        # Create test users

        # Create a user in the MCP User group
        self.mcp_user = create_test_user(
            self.env,
            "MCP User",
            "mcp_user",
            email="mcp_user@example.com",
            groups_id=[(6, 0, [self.env.ref("mcp_server.group_mcp_user").id])],
        )

        # Create a user in the MCP Admin group
        self.mcp_admin = create_test_user(
            self.env,
            "MCP Admin",
            "mcp_admin",
            email="mcp_admin@example.com",
            groups_id=[(6, 0, [self.env.ref("mcp_server.group_mcp_admin").id])],
        )

        # Create a regular user without MCP access
        self.regular_user = create_test_user(
            self.env,
            "Regular User",
            "regular_user",
            email="regular_user@example.com",
            groups_id=[(6, 0, [self.env.ref("base.group_user").id])],
        )

        # Check if the model already exists in database
        partner_model_id = self.env.ref("base.model_res_partner").id
        existing_model = (
            self.env["mcp.enabled.model"]
            .sudo()
            .search([("model_id", "=", partner_model_id)], limit=1)
        )

        if existing_model:
            self.test_model = existing_model
        else:
            # Create test enabled model
            self.test_model = (
                self.env["mcp.enabled.model"]
                .sudo()
                .create(
                    {
                        "model_id": partner_model_id,
                        "allow_read": True,
                        "allow_create": False,
                        "allow_write": False,
                        "allow_unlink": False,
                    }
                )
            )

    def test_mcp_admin_access(self):
        """Test that MCP Admin can read and modify MCP settings"""
        # Switch to admin user
        enabled_model = self.test_model.with_user(self.mcp_admin)

        # Verify admin can read
        self.assertTrue(
            enabled_model.model_id.name,
            "Admin should be able to read MCP enabled models",
        )

        # Find a model that isn't already enabled
        company_model_id = self.env.ref("base.model_res_company").id
        existing_model = (
            self.env["mcp.enabled.model"]
            .with_user(self.mcp_admin)
            .search([("model_id", "=", company_model_id)], limit=1)
        )

        if existing_model:
            # If it already exists, we'll just verify we can write to it
            existing_model.write({"allow_create": True})
            self.assertTrue(
                existing_model.allow_create,
                "Admin should be able to modify MCP enabled models",
            )
            new_model = existing_model
        else:
            # Verify admin can create
            new_model = (
                self.env["mcp.enabled.model"]
                .with_user(self.mcp_admin)
                .create(
                    {
                        "model_id": company_model_id,
                        "allow_read": True,
                    }
                )
            )
            self.assertTrue(
                new_model.id, "Admin should be able to create MCP enabled models"
            )

            # Verify admin can write
            enabled_model.with_user(self.mcp_admin).write({"allow_create": True})
            self.assertTrue(
                enabled_model.allow_create,
                "Admin should be able to modify MCP enabled models",
            )

        # Verify admin can unlink (only if we created it in this test)
        if not existing_model:
            new_model.with_user(self.mcp_admin).unlink()
            self.assertFalse(
                self.env["mcp.enabled.model"].search([("id", "=", new_model.id)]),
                "Admin should be able to delete MCP enabled models",
            )

    def test_mcp_user_access(self):
        """Test that MCP User can read but not modify MCP settings"""
        # Switch to user
        enabled_model = self.test_model.with_user(self.mcp_user)

        # Verify user can read
        self.assertTrue(
            enabled_model.model_id.name,
            "User should be able to read MCP enabled models",
        )

        # Verify user cannot create
        with self.assertRaises(
            AccessError, msg="User should not be able to create MCP enabled models"
        ):
            self.env["mcp.enabled.model"].with_user(self.mcp_user).create(
                {
                    "model_id": self.env.ref("base.model_res_company").id,
                    "allow_read": True,
                }
            )

        # Verify user cannot write
        with self.assertRaises(
            AccessError, msg="User should not be able to modify MCP enabled models"
        ):
            enabled_model.with_user(self.mcp_user).write({"allow_create": True})

        # Verify user cannot unlink
        with self.assertRaises(
            AccessError, msg="User should not be able to delete MCP enabled models"
        ):
            enabled_model.with_user(self.mcp_user).unlink()

    def test_regular_user_access(self):
        """Test that regular users have no access to MCP settings"""
        # Attempt to access as regular user
        with self.assertRaises(
            AccessError,
            msg="Regular user should not be able to read MCP enabled models",
        ):
            # Access the attribute to trigger the access error
            _ = self.test_model.with_user(self.regular_user).model_id.name

    def test_settings_menu_access(self):
        """Test MCP Admin can access settings menu but MCP User cannot"""
        # Try to find the MCP menu by ref first
        try:
            menu_root = self.env.ref("mcp_server.mcp_menu_technical")
        except ValueError:
            # Fallback to search
            menu_root = self.env["ir.ui.menu"].search([("name", "=", "MCP")], limit=1)

        if not menu_root:
            self.skipTest("Menu 'MCP' not found, skipping test")

        # Get the groups
        mcp_admin_group = self.env.ref("mcp_server.group_mcp_admin")
        mcp_user_group = self.env.ref("mcp_server.group_mcp_user")

        # Check if MCP Admin has access to the menu
        # The menu should be restricted to mcp_admin group only
        self.assertIn(
            mcp_admin_group,
            menu_root.groups_id,
            "Menu should be restricted to MCP Admin group",
        )

        # Check that the menu is NOT directly accessible to MCP User group
        # Even though mcp_admin implies mcp_user, the menu should only list mcp_admin
        self.assertNotIn(
            mcp_user_group,
            menu_root.groups_id,
            "Menu should NOT be directly accessible to MCP User group",
        )

        # Verify actual access using check_access_rights
        # MCP Admin should have access
        menu_as_admin = menu_root.with_user(self.mcp_admin)
        self.assertTrue(
            menu_as_admin._filter_visible_menus(),
            "MCP Admin should have access to the menu",
        )

        # MCP User should NOT have access
        menu_as_user = menu_root.with_user(self.mcp_user)
        self.assertFalse(
            menu_as_user._filter_visible_menus(),
            "MCP User should NOT have access to the menu",
        )
