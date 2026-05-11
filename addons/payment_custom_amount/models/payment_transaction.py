# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransactionCustomAmount(models.Model):
    _inherit = 'payment.transaction'

    def _get_processing_values(self):
        res = super()._get_processing_values()

        _logger.info(
            ">>> [TX] _get_processing_values ANTES: amount=%s, ref=%s",
            res.get('amount'),
            self.reference,
        )

        try:
            from odoo.http import request as http_request
            if http_request and hasattr(http_request, 'session'):
                custom_amount = http_request.session.get('custom_payment_amount')

                _logger.info(
                    ">>> [TX] Sesión custom_payment_amount=%s", custom_amount
                )

                if custom_amount and float(custom_amount) > 0:
                    original = res.get('amount')
                    res['amount'] = float(custom_amount)

                    # También actualizar el campo en la transacción misma
                    # para que el registro en BD quede correcto
                    self.sudo().write({'amount': float(custom_amount)})

                    # Limpiar sesión — ya fue consumida
                    http_request.session.pop('custom_payment_amount', None)

                    _logger.info(
                        ">>> [TX] ✅ amount reemplazado: %.2f → %.2f",
                        original,
                        custom_amount,
                    )

        except Exception as e:
            _logger.error(">>> [TX] ❌ Error leyendo sesión: %s", e)

        _logger.info(
            ">>> [TX] _get_processing_values DESPUÉS: amount=%s", res.get('amount')
        )

        return res