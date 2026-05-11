# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.addons.account_payment.controllers.portal import PortalAccount

_logger = logging.getLogger(__name__)

_logger.info(">>> PAYMENT_PAY recibido: amount=%s, access_token=%s", amount, access_token)

class PaymentCustomAmountPortal(PortalAccount):

    @http.route()
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        # 1. Extraer valores del formulario
        custom_amount = kwargs.get('custom_payment_amount')
        custom_type = kwargs.get('custom_payment_type')

        if custom_type == 'custom' and custom_amount:
            try:
                amount_float = float(custom_amount)
                # GUARDAR EN SESIÓN: Esto es vital para que el modelo lo vea
                request.session['custom_payment_amount'] = amount_float
                
                # FORZAR EN KWARGS: Odoo busca la llave 'amount'
                kwargs['amount'] = amount_float
                
                _logger.info(">>> [PORTAL] Inyectando monto personalizado en sesión: %.2f", amount_float)
            except (ValueError, TypeError):
                _logger.error(">>> [PORTAL] Error al convertir monto: %s", custom_amount)

        return super().invoice_transaction(invoice_id, access_token, **kwargs)