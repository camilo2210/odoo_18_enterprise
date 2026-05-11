# -*- coding: utf-8 -*-
import logging
from odoo import models, api, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0

def _pop_custom_amount():
    """ Lee y extrae el monto de la sesión HTTP """
    try:
        if request and hasattr(request, 'session'):
            return request.session.pop('custom_payment_amount', None)
    except Exception:
        pass
    return None

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model_create_multi
    def create(self, vals_list):
        """ 
        Paso 1: Al crear la transacción, si hay un monto en sesión, 
        lo forzamos en el campo 'amount'.
        """
        custom_amount = _pop_custom_amount()
        for vals in vals_list:
            if custom_amount and vals.get('move_id'):
                vals['amount'] = float(custom_amount)
                _logger.info("TX Create: Aplicando monto personalizado %.2f desde sesión", vals['amount'])
        
        # Si sacamos el monto de la sesión, lo volvemos a poner temporalmente 
        # para que el método de Mercado Pago también lo vea si es necesario.
        if custom_amount:
            request.session['custom_payment_amount'] = custom_amount
            
        return super().create(vals_list)

    def _mercado_pago_prepare_preference_request_payload(self):
        """
        Paso 2: Garantía final para Mercado Pago.
        Si por alguna razón Odoo recalculó el total, aquí lo volvemos a forzar
        directamente en la base de datos antes de generar el JSON.
        """
        res = super()._mercado_pago_prepare_preference_request_payload()
        
        # Recuperamos y limpiamos definitivamente la sesión
        custom_amount = _pop_custom_amount()
        
        if custom_amount:
            custom_amount = float(custom_amount)
            # Actualización directa por SQL para evitar re-cálculos del ORM
            self.env.cr.execute(
                "UPDATE payment_transaction SET amount = %s WHERE id = %s",
                (custom_amount, self.id)
            )
            # Invalidamos caché para que self.amount devuelva el nuevo valor
            self.invalidate_recordset(['amount'])
            
            _logger.info("TX %s: Payload MP forzado a %.2f", self.reference, custom_amount)
            
            # Actualizamos el payload que ya se generó en el super()
            if 'items' in res and len(res['items']) > 0:
                res['items'][0]['unit_price'] = custom_amount
                # Si el addon envía varios items, es mejor colapsarlos a uno solo con el monto personalizado
                if len(res['items']) > 1:
                    res['items'] = [{
                        'title': f"Pago parcial factura {self.reference}",
                        'quantity': 1,
                        'unit_price': custom_amount,
                        'currency_id': self.currency_id.name,
                    }]

        return res