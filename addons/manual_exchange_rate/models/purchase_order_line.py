from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    manual_rate_display = fields.Float(
        related='order_id.manual_rate_display',
        string="Manual Exchange Rate",
        store=False,
        readonly=False,
    )
    is_exchange = fields.Boolean(
        related='order_id.is_exchange',
        store=False,
        readonly=False,
    )
    rate = fields.Float(
        related='order_id.rate',
        store=False,
        readonly=False,
    )
    # خليها related مخزنة عشان Monetary field
    company_currency_id = fields.Many2one(
        'res.currency',
        related='order_id.currency_id',
        store=True,
        readonly=True
    )

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_price_subtotal',
        currency_field='company_currency_id'
    )

    @api.depends('price_unit', 'product_qty')
    def _compute_price_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.price_unit * rec.product_qty
