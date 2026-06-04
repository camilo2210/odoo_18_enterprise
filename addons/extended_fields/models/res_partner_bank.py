# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    pgm_iban = fields.Char(
        string="IBAN",
        help="IBAN code of the bank account."
    )
    
    account_type = fields.Selection(
        [
            ('a', 'Savings'), 
            ('c', 'Checking')
        ], 
        'Account Type', 
        required=True, 
        default='a', 
        help="Account Type: Savings & Checking"
    )
    
    is_intermediario = fields.Boolean(string="Intermediary", default=False)