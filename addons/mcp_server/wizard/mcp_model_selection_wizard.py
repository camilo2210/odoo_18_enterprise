from odoo import api, fields, models


class McpModelSelectionWizard(models.TransientModel):
    """Wizard for selecting multiple models to enable for MCP access at once."""

    _name = "mcp.model.selection.wizard"
    _description = "MCP Model Selection Wizard"

    @api.model
    def _get_model_domain(self):
        # Get already enabled models
        enabled_model_ids = (
            self.env["mcp.enabled.model"].search([]).mapped("model_id.id")
        )
        domain = [
            ("transient", "=", False),
            ("model", "not like", "ir.%"),
            ("model", "not like", "base_%"),
        ]
        if enabled_model_ids:
            domain.append(("id", "not in", enabled_model_ids))
        return domain

    model_ids = fields.Many2many(
        "ir.model",
        string="Models",
        required=True,
        domain=lambda self: self._get_model_domain(),
        help="Select models to enable for MCP access",
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

    def action_enable_models(self):
        """Enable selected models for MCP access."""
        self.ensure_one()
        for model in self.model_ids:
            # Check if model is already enabled
            existing = self.env["mcp.enabled.model"].search(
                [("model_id", "=", model.id)], limit=1
            )
            if not existing:
                # Create new enabled model record
                self.env["mcp.enabled.model"].create(
                    {
                        "model_id": model.id,
                        "allow_read": self.allow_read,
                        "allow_create": self.allow_create,
                        "allow_write": self.allow_write,
                        "allow_unlink": self.allow_unlink,
                    }
                )
        return {"type": "ir.actions.act_window_close"}
