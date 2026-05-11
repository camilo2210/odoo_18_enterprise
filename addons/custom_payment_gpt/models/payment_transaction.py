from odoo import api, models
from odoo.http import request


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    @api.model
    def create(self, vals):

        custom_amount = None

        try:
            custom_amount = request.session.get("custom_payment_amount")
        except Exception:
            pass

        if custom_amount:
            vals["amount"] = float(custom_amount)

            try:
                request.session.pop("custom_payment_amount")
            except Exception:
                pass

        return super().create(vals)