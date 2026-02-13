from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class BnCompany(models.Model):
    _inherit = 'res.company'

    second_currency_id = fields.Many2one(
        'res.currency',
        string='Second Currency',
        help="Second currency of the company."
    )

    enable_second_currency_for_company = fields.Boolean('Enable Second Currency', store=True)
