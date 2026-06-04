# -*- coding: utf-8 -*-
from odoo import fields, models


class ResBank(models.Model):
    _inherit = 'res.bank'

    pgm_abba = fields.Char(
        string="ABBA",
        help="Bank's ABBA/Routing code."
    )

    pgm_swift = fields.Char(
        string="SWIFT",
        help="Bank's SWIFT/BIC code."
    )
    pgm_vat = fields.Char(string='Vat')
