from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class IrActionsActions(models.Model):
    """Extend ir.actions.actions to integrate simplified access control."""

    _inherit = "ir.actions.actions"

    def create(self, vals):
        """Automatically create corresponding action.data record on creation."""
        action = super().create(vals)
        self.env["action.data"].create({"action_id": action.id})
        return action

    def unlink(self):
        """Remove corresponding action.data records when deleting actions."""
        action_data = self.env["action.data"].search([("action_id", "in", self.ids)])
        if action_data:
            action_data.unlink()
        return super().unlink()

    @api.model
    def get_bindings(self, model_name):
        """Filter out restricted actions and reports for this model."""
        result = super().get_bindings(model_name)
        
        cached = self.env["model.access"].get_cached_model_access(model_name)
        result["action"] = [
            a for a in result.get("action", [])
            if a and a.get("id") not in cached["restricted_actions_ids"]
        ]
        result["report"] = [
            r for r in result.get("report", [])
            if r and r.get("id") not in cached["restricted_reports_ids"]
        ]
        return result
