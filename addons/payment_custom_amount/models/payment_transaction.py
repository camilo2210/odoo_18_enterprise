    # models/payment_transaction.py
# -*- coding: utf-8 -*-
import logging
from odoo import models, api
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_processing_values(self):
        """
        Override del método que construye los valores enviados al proveedor.
        Es el ÚNICO punto seguro para modificar el amount antes de que
        Mercado Pago / ePayco reciban el JSON — ocurre después de que
        el controlador ya validó el HMAC del token.
        """
        # Recuperar monto personalizado de la sesión
        custom_amount = None
        try:
            if request and hasattr(request, 'session'):
                custom_amount = request.session.pop('custom_payment_amount', None)
        except RuntimeError:
            # Fuera de contexto HTTP (cron, test, etc.)
            pass

        if custom_amount is not None:
            try:
                custom_amount = float(custom_amount)
                min_amount = float(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'payment_custom_amount.min_amount', default='1500.0'
                    )
                )
                min_amount = max(min_amount, 1500.0)

                if custom_amount >= min_amount and custom_amount <= self.amount:
                    _logger.info(
                        'TX %s: aplicando monto personalizado %.2f (original: %.2f)',
                        self.reference, custom_amount, self.amount,
                    )
                    # Modificar el amount en el recordset antes de procesar
                    self.sudo().write({'amount': custom_amount})
                else:
                    _logger.warning(
                        'TX %s: monto personalizado %.2f fuera de rango [%.2f, %.2f] — ignorado',
                        self.reference, custom_amount, min_amount, self.amount,
                    )
            except (TypeError, ValueError) as e:
                _logger.warning('TX %s: monto personalizado inválido: %s', self.reference, str(e))

        return super()._get_processing_values()