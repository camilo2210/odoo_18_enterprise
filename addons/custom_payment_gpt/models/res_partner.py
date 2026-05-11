from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    allow_custom_portal_amount = fields.Boolean(
        string="Allow Custom Portal Payment Amount",
        help="Allow this customer to enter a custom amount when paying invoices from the portal."
    )