from odoo import http, _
from odoo.http import request
# CORRECCIÓN PARA V18: La clase correcta es PaymentPortal
from odoo.addons.website_payment.controllers.portal import PaymentPortal

class CustomPaymentPortal(PaymentPortal):

    @http.route()
    def payment_transaction(self, amount=None, invoice_id=None, **kwargs):
        """ 
        Extensión para permitir abonos parciales validados.
        """
        if invoice_id:
            # Buscamos la factura con sudo para evitar errores de acceso en el portal
            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            
            if amount:
                try:
                    # Convertimos el monto ingresado a flotante
                    custom_amount = float(amount)
                except ValueError:
                    return {'error': _("El monto ingresado no es válido.")}

                # VALIDACIÓN 1: No exceder el saldo residual de la factura
                if custom_amount > invoice.amount_residual:
                    return {'error': _("El monto no puede ser superior al saldo pendiente (%s).") % invoice.amount_residual}

                # VALIDACIÓN 2: Monto mínimo (Ejemplo: 1,500 COP para Mercado Pago)
                if invoice.currency_id.name == 'COP' and custom_amount < 1500:
                    return {'error': _("El monto mínimo para procesar el pago es de 1,500 COP.")}

                # Sobrescribimos el monto para la transacción
                kwargs['amount'] = custom_amount

        return super().payment_transaction(amount=amount, invoice_id=invoice_id, **kwargs)