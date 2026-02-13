import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ActionData(models.Model):
    """Reference model for managing Odoo actions in access control rules."""

    _name = "action.data"
    _description = "Action Data"

    action_id = fields.Many2one(
        "ir.actions.actions",
        string="Action",
        required=True,
        ondelete="cascade",
        help="Odoo action to be managed by access control rules.",
    )

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
        help="Computed name of the selected action.",
    )

    @api.depends("action_id")
    def _compute_name(self):
        """Compute the name field based on the selected action."""
        for rec in self:
            rec.name = rec.action_id.name
