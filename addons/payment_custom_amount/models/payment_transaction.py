cat > /home/ubuntu/carpeta_odoo/addons/payment_custom_amount/models/payment_transaction.py << 'PYEOF'
# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


def _pop_custom_amount(env):
    """
    Lee y elimina el monto personalizado de la sesión HTTP.
    Retorna float o None si no hay sesión / no hay valor.
    """
    try:
        if request and hasattr(request, 'session'):
            value = request.session.pop('custom_payment_amount', None)
            if value is not None:
                return float(value)
    except RuntimeError:
        pass
    except (TypeError, ValueError) as e:
        _logger.warning('Monto personalizado inválido en sesión: %s', str(e))
    return None


def _get_global_min(env):
    try:
        val = float(
            env['ir.config_parameter'].sudo().get_param(
                'payment_custom_amount.min_amount',
                default=str(MERCADO_PAGO_COLOMBIA_MIN),
            )
        )
        return max(val, MERCADO_PAGO_COLOMBIA_MIN)
    except Exception:
        return MERCADO_PAGO_COLOMBIA_MIN


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _mercado_pago_prepare_preference_request_payload(self):
        """
        Override del método que construye el JSON enviado a Mercado Pago.
        Es el punto más seguro para aplicar el monto personalizado porque:
        - Se ejecuta justo antes de llamar a la API de MP
        - unit_price = self.amount se lee DESPUÉS de nuestro cambio
        - No depende del caché del ORM ni de llamadas previas
        """
        custom_amount = _pop_custom_amount(self.env)

        if custom_amount is not None:
            min_amount = _get_global_min(self.env)
            original  = self.amount

            if custom_amount >= min_amount and custom_amount <= original:
                _logger.info(
                    'TX %s | MP payload: aplicando monto personalizado %.2f '
                    '(original: %.2f)',
                    self.reference, custom_amount, original,
                )
                # Modificar directamente en memoria el campo amount
                # para que unit_price = self.amount tome el valor correcto
                self.env.cr.execute(
                    'UPDATE payment_transaction SET amount = %s WHERE id = %s',
                    (custom_amount, self.id)
                )
                self.invalidate_recordset(['amount'])
            else:
                _logger.warning(
                    'TX %s | MP payload: monto personalizado %.2f fuera de '
                    'rango [%.2f, %.2f] — ignorado, se usará monto original',
                    self.reference, custom_amount, min_amount, original,
                )

        return super()._mercado_pago_prepare_preference_request_payload()
PYEOF
echo "✅ payment_transaction.py actualizado"