import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ViewType(models.Model):
    """View type definitions for access control restrictions."""

    _name = "ir.ui.view.type"
    _description = "View Type"

    name = fields.Char(
        string="Name",
        required=True,
        help="The user-friendly name of the view, e.g., 'List', 'Form'.",
    )

    techname = fields.Char(
        string="Technical Name",
        required=True,
        help="The technical identifier of the view, e.g., 'list', 'form'.",
    )

    _sql_constraints = [
        ("unique_techname", "unique(techname)", "The technical name must be unique!"),
        ("unique_name", "unique(name)", "The view name must be unique!"),
    ]

    @api.constrains("techname")
    def _validate_techname_format(self):
        """Ensure technical name is stored in lowercase for consistency."""
        for rec in self:
            if rec.techname and rec.techname != rec.techname.lower():
                raise ValidationError(_("Technical Name must be in lowercase."))
