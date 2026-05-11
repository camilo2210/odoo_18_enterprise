from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _prepare_transaction_values(self, *args, **kwargs):
        values = super()._prepare_transaction_values(*args, **kwargs)
        
        # El valor vendrá capturado desde el controlador (Archivo 3)
        custom_amount = self.env.context.get('custom_amount')
        
        if custom_amount:
            amount = float(custom_amount)
            # Validación de seguridad: No puede ser superior al saldo residual
            invoice = self.env['account.move'].browse(kwargs.get('invoice_id'))
            if invoice and amount > invoice.amount_residual:
                raise ValidationError(_("El monto del abono no puede superar el saldo pendiente."))
            
            values['amount'] = amount
            
        return values