from odoo import api, fields, models
import logging

from ast import literal_eval

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    second_currency_id = fields.Many2one('res.currency', related="company_id.second_currency_id", required=False,
                                         readonly=False,
                                         string='Second Currency', help="Second currency of the company.")

    enable_second_currency_for_company = fields.Boolean(related='company_id.enable_second_currency_for_company')
