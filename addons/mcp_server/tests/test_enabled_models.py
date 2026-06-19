from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("much_unit", "post_install", "-at_install")
class TestMcpEnabledModels(TransactionCase):
    """Test the MCP enabled models functionality."""

    def setUp(self):
        super().setUp()
        # Get the model for partner as a test case
        self.partner_model = self.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        self.user_model = self.env["ir.model"].search(
            [("model", "=", "res.users")], limit=1
        )

        # Ensure test isolation by cleaning up any existing
        # res.users enabled model records
        # that might have been created by other tests
        existing_user_models = self.env["mcp.enabled.model"].search(
            [("model_id", "=", self.user_model.id)]
        )
        if existing_user_models:
            existing_user_models.unlink()

        # Check if the model already exists in database
        existing_model = self.env["mcp.enabled.model"].search(
            [("model_id", "=", self.partner_model.id)], limit=1
        )

        if existing_model:
            # Update the existing model to have the permissions we need for testing
            existing_model.write(
                {
                    "allow_read": True,
                    "allow_create": True,
                    "allow_write": False,
                    "allow_unlink": False,
                    "active": True,
                }
            )
            self.enabled_model = existing_model
        else:
            # Create a test enabled model
            self.enabled_model = self.env["mcp.enabled.model"].create(
                {
                    "model_id": self.partner_model.id,
                    "allow_read": True,
                    "allow_create": True,
                    "allow_write": False,
                    "allow_unlink": False,
                }
            )

    def test_model_enabled(self):
        """Test if a model is correctly marked as enabled."""
        # Check that our test model is enabled
        self.assertTrue(
            self.env["mcp.enabled.model"].is_model_enabled("res.partner"),
            "Partner model should be enabled for MCP access",
        )

        # Check that a non-enabled model is correctly identified
        self.assertFalse(
            self.env["mcp.enabled.model"].is_model_enabled("res.users"),
            "User model should not be enabled for MCP access",
        )

    def test_operation_permissions(self):
        """Test if operation permissions are correctly checked."""
        # Test allowed operations
        self.assertTrue(
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.partner", "read"
            ),
            "Read operation should be allowed for partner model",
        )
        self.assertTrue(
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.partner", "create"
            ),
            "Create operation should be allowed for partner model",
        )

        # Test disallowed operations
        self.assertFalse(
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.partner", "write"
            ),
            "Write operation should not be allowed for partner model",
        )
        self.assertFalse(
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.partner", "unlink"
            ),
            "Unlink operation should not be allowed for partner model",
        )

        # Test non-enabled model
        self.assertFalse(
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.users", "read"
            ),
            "Read operation should not be allowed for non-enabled model",
        )

    def test_model_deactivation(self):
        """Test if deactivating a model works correctly."""
        # Deactivate the model
        self.enabled_model.active = False

        # Check that it's now seen as not enabled
        self.assertFalse(
            self.env["mcp.enabled.model"].is_model_enabled("res.partner"),
            "Deactivated model should not be enabled for MCP access",
        )

        # Reactivate and check again
        self.enabled_model.active = True
        self.assertTrue(
            self.env["mcp.enabled.model"].is_model_enabled("res.partner"),
            "Reactivated model should be enabled for MCP access",
        )

    def test_invalid_operation(self):
        """Test handling of invalid operations."""
        with self.assertRaises(ValidationError):
            self.env["mcp.enabled.model"].check_model_operation_enabled(
                "res.partner", "invalid_operation"
            )

    @mute_logger("odoo.sql_db")
    def test_unique_constraint(self):
        """Test that the same model cannot be enabled twice."""
        # Try to create another record for the same model
        # Find a different model to use for this test
        different_model = self.env["ir.model"].search(
            [
                ("model", "not like", "ir.%"),
                ("model", "not like", "base_%"),
                ("id", "!=", self.partner_model.id),
                ("transient", "=", False),
            ],
            limit=1,
        )

        # First, ensure no existing enabled record for this model
        existing = self.env["mcp.enabled.model"].search(
            [("model_id", "=", different_model.id)]
        )
        if existing:
            existing.unlink()

        # Create the first record
        first_record = self.env["mcp.enabled.model"].create(
            {
                "model_id": different_model.id,
                "allow_read": True,
            }
        )

        # Now try to create a duplicate, which should fail
        # The model has an SQL constraint, so it will raise IntegrityError
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(IntegrityError):
                self.env["mcp.enabled.model"].create(
                    {
                        "model_id": different_model.id,
                        "allow_read": True,
                    }
                )

        # Clean up
        first_record.unlink()

    def test_ondelete_cascade(self):
        """Test cascade deletion when model is deleted."""
        # Create a temporary model
        temp_model = self.env["ir.model"].create(
            {
                "name": "Temporary Test Model",
                "model": "x_temp.test.model",
            }
        )

        # Enable it for MCP
        temp_enabled = self.env["mcp.enabled.model"].create(
            {
                "model_id": temp_model.id,
            }
        )

        # Verify it exists
        self.assertTrue(temp_enabled.exists())

        # Delete the model - the enabled record should be deleted due to cascade
        temp_model.unlink()
        self.assertFalse(
            temp_enabled.exists(),
            "Enabled model record should be deleted when the model is deleted",
        )
