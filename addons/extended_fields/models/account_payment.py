# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Purchase Order",
        domain="[('partner_id', '=', partner_id), ('state', 'in', ('purchase','done')), ('invoice_status', '!=', 'invoiced')]",
        context={'display_po_amount': True},  # <- clave para formateo en name_get
        help="Vendors purchase orders related to the payment, confirmed or finalized, and not yet fully invoiced."
    )
    
    pgm_bank_account_currency_id = fields.Many2one(
        'res.currency',
        string="Currency of Bank Account",
        related='partner_bank_id.currency_id',
        store=True,
        readonly=True,
        help="Currency of the bank account associated with the payment."
    )

    
    @api.constrains('purchase_order_id', 'partner_type')
    def _check_supplier_when_po(self):
        for rec in self:
            if rec.purchase_order_id and rec.partner_type and rec.partner_type != 'supplier':
                raise ValidationError(
                    _("'Purchase Order' is only applicable to vendor payments.")
                )
