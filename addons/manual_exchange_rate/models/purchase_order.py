# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Farook Al Ameen (odoo@cybrosys.info)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models

class PurchaseOrder(models.Model):
    """This class extends the base 'purchase.order' model to introduce a
    new field, 'is_exchange',which allows users to manually apply an exchange
    rate for a transaction. When this option is enabled, users can specify
    the exchange rate through the 'rate' field."""
    _inherit = 'purchase.order'

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True, help="To store the Company Currency")
    is_exchange = fields.Boolean(string='Apply Manual Currency', help='allows users to manually apply an exchange rate')
    rate = fields.Float(string='Rate', help='specify the rate', default=1)
    manual_rate_display = fields.Float(
        string="Manual Exchange Rate",
        help="Enter how many Your Currency per 1 USD (or vice versa depending on your needs)."
    )

    #Monetary
    purchase_line_ids = fields.One2many(
        'purchase.order.line', 'order_id', string="Purchase Lines"
    )
    amount_total_company_currency = fields.Monetary(
        string="Total in Company Currency",
        compute="_compute_amount_total_company_currency",
        currency_field="company_currency_id",
        store=False
    )


    amount_total_company_manual = fields.Monetary(
        string="Total in Company Currency (Manual)",
        compute="_compute_amount_total_company_manual",
        currency_field="company_currency_id",
        store=False
    )

    @api.depends('amount_total', 'rate')
    def _compute_amount_total_company_manual(self):
        for order in self:
            if order.rate:
                order.amount_total_company_manual = order.amount_total / order.rate
            else:
                order.amount_total_company_manual = 0.0








    @api.constrains('company_currency_id', 'currency_id')
    def _onchange_different_currency(self):
        """ When the Currency is changed back to company currency, the boolean field is disabled """
        if self.company_currency_id == self.currency_id:
            if self.is_exchange:
                self.is_exchange = False

    @api.onchange('is_exchange')
    def _onchange_is_exchange(self):
        """ Update Rate when is_exchange is Enabled."""
        if self.is_exchange:
            self.rate = self.env['res.currency']._get_conversion_rate(
                from_currency=self.company_currency_id,
                to_currency=self.currency_id,
                company=self.company_id,
                date=self.date_order)
            if self.manual_rate_display:
                self.rate = self.manual_rate_display

    @api.onchange('manual_rate_display')
    def _onchange_manual_rate_display(self):
        """لما المستخدم يدخل السعر اليدوي نحسب المقلوب ونباصيه للـ rate"""
        if self.is_exchange and self.manual_rate_display:
            try:
                self.rate = 1 / float(self.manual_rate_display)
            except ZeroDivisionError:
                self.rate = 1




    custom_tax_total = fields.Monetary(
        string="Custom Tax Total",
        compute="_compute_custom_tax_total",
        currency_field='currency_id',
        store=False,
    )

    custom_total = fields.Monetary(
        string="Custom Total",
        compute="_compute_custom_total",
        currency_field='currency_id',
        store=False,
    )

    @api.depends('order_line.price_unit', 'order_line.product_qty', 'order_line.taxes_id')
    def _compute_custom_tax_total(self):
        for order in self:
            total_tax = 0.0
            for line in order.order_line:
                if line.taxes_id:
                    taxes = line.taxes_id.compute_all(
                        line.price_unit,
                        order.currency_id,
                        line.product_qty,
                        product=line.product_id,
                        partner=order.partner_id,
                    )
                    total_tax += taxes['total_included'] - taxes['total_excluded']
            order.custom_tax_total = total_tax

    @api.depends('order_line.price_subtotal', 'custom_tax_total')
    def _compute_custom_total(self):
        for order in self:
            subtotal = sum(order.order_line.mapped('price_subtotal'))
            order.custom_total = subtotal + order.custom_tax_total
