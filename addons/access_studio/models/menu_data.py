import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MenuData(models.Model):
    """Reference model for managing Odoo menus in access control rules."""

    _name = "menu.data"
    _description = "Menu Data"

    # Basic Fields

    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu",
        required=True,
        ondelete="cascade",
        help="Odoo menu to be managed by access control rules.",
    )

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
        help="Computed name of the selected menu.",
    )

    # Computed Methods

    @api.depends("menu_id")
    def _compute_name(self):
        """Compute the name field based on the selected menu."""
        for rec in self:
            rec.name = rec.menu_id.display_name
