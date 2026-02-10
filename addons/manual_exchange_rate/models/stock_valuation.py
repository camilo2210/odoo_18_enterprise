from odoo import models, api, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_id = vals.get('stock_move_id')
            quantity = vals.get('quantity') or 0.0

            if move_id and quantity:
                move = self.env['stock.move'].browse(move_id)
                pol = move.purchase_line_id
                po = pol.order_id if pol else None

                if pol and po and po.currency_id != po.company_id.currency_id:
                    unit_price_foreign = pol.price_unit

                    if pol.is_exchange and pol.rate:
                        converted_price_unit = unit_price_foreign / pol.rate
                    else:
                        converted_price_unit = po.currency_id._convert(
                            unit_price_foreign,
                            po.company_id.currency_id,
                            po.company_id,
                            po.date_order or fields.Date.today()
                        )

                    vals['value'] = quantity * converted_price_unit
                    vals['unit_cost'] = converted_price_unit

        return super().create(vals_list)
