from odoo import http, _
from odoo.http import request
from odoo.addons.website_payment.controllers.portal import WebsitePaymentPortal

class CustomWebsitePaymentPortal(WebsitePaymentPortal):

    @http.route()
    def payment_transaction(self, amount=None, invoice_id=None, **kwargs):
        """
        Sobreescribimos la ruta que genera la transacción para aplicar 
        las validaciones de abono libre y mínimos de Mercado Pago.
        """
        if invoice_id and amount:
            invoice = request.env['account.move'].browse(int(invoice_id))
            partner = invoice.partner_id

            # 1. Verificar si el cliente tiene permitido el abono parcial
            if partner.x_allow_partial_portal_payment:
                try:
                    custom_amount = float(amount)
                except ValueError:
                    return {'error': _("Monto inválido.")}

                # 2. Validación de Mínimo para Mercado Pago (1,500 COP)
                if invoice.currency_id.name == 'COP' and custom_amount < 1500:
                    return {'error': _("El abono mínimo permitido es de 1,500 COP.")}

                # 3. Validación de Máximo (No pagar más de lo que debe)
                if custom_amount > invoice.amount_residual:
                    return {'error': _("El monto no puede ser superior al saldo pendiente.")}
                
                # Pasamos el monto validado al flujo estándar
                kwargs['amount'] = custom_amount

        return super().payment_transaction(amount=amount, invoice_id=invoice_id, **kwargs)