from odoo import http, _
from odoo.http import request
# CORRECCIÓN V18: Cambiamos WebsitePaymentPortal por WebsitePayment
from odoo.addons.website_payment.controllers.portal import WebsitePayment

class CustomWebsitePayment(WebsitePayment): # Heredamos de la clase correcta

    @http.route()
    def payment_transaction(self, amount=None, invoice_id=None, **kwargs):
        """
        Lógica para validar el abono parcial personalizado.
        """
        if invoice_id and amount:
            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            partner = invoice.partner_id

            if partner.x_allow_partial_portal_payment:
                try:
                    custom_amount = float(amount)
                except ValueError:
                    return {'error': _("Monto inválido.")}

                # Validación del mínimo de Mercado Pago (1,500 COP)
                if invoice.currency_id.name == 'COP' and custom_amount < 1500:
                    return {'error': _("El abono mínimo permitido es de 1,500 COP.")}

                if custom_amount > invoice.amount_residual:
                    return {'error': _("El monto no puede ser superior al saldo pendiente.")}
                
                kwargs['amount'] = custom_amount

        return super().payment_transaction(amount=amount, invoice_id=invoice_id, **kwargs)