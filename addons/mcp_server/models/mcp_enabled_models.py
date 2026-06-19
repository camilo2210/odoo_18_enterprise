from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class McpEnabledModel(models.Model):
    """Model to store which Odoo models are enabled for MCP access.

    This model allows administrators to selectively expose models
    through the MCP interface.
    """

    _name = "mcp.enabled.model"
    _description = "MCP Enabled Model"
    _rec_name = "model_id"

    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        index=True,
        ondelete="cascade",
        help="The Odoo model to be enabled for MCP access",
    )
    model_name = fields.Char(
        related="model_id.model", string="Technical Name", store=True, readonly=True
    )
    active = fields.Boolean(
        default=True,
        help="Indicates whether this model is enabled for MCP access",
    )
    allow_read = fields.Boolean(default=True, help="Allow read operations through MCP")
    allow_create = fields.Boolean(
        default=False, help="Allow create operations through MCP"
    )
    allow_write = fields.Boolean(
        string="Allow Update", default=False, help="Allow update operations through MCP"
    )
    allow_unlink = fields.Boolean(
        string="Allow Delete", default=False, help="Allow delete operations through MCP"
    )
    notes = fields.Text(help="Additional notes about this model configuration")

    _sql_constraints = [
        (
            "unique_model",
            "UNIQUE(model_id)",
            "A model can only be enabled once for MCP access.",
        )
    ]

    @api.model
    def is_model_enabled(self, model_name):
        """Check if a model is enabled for MCP access.

        Args:
            model_name (str): The technical name of the model

        Returns:
            bool: True if the model is enabled, False otherwise
        """
        record = self.search(
            [("model_name", "=", model_name), ("active", "=", True)], limit=1
        )
        return bool(record)

    @api.model
    def check_model_operation_enabled(self, model_name, operation):
        """Check if a specific operation is enabled for a model.

        Args:
            model_name (str): The technical name of the model
            operation (str): One of 'read', 'create', 'write', 'unlink'

        Returns:
            bool: True if the operation is enabled, False otherwise

        Raises:
            ValidationError: If an invalid operation is specified
        """
        if operation not in ["read", "create", "write", "unlink"]:
            raise ValidationError(_("Invalid operation: %s") % operation)

        record = self.search(
            [("model_name", "=", model_name), ("active", "=", True)], limit=1
        )

        if not record:
            return False

        return bool(record["allow_" + operation])
