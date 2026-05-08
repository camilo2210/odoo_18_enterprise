# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_custom_min_amount = fields.Float(
        string='Monto minimo para pago personalizado (COP)',
        default=MERCADO_PAGO_COLOMBIA_MIN,
        config_parameter='payment_custom_amount.min_amount',
        help=(
            'Monto minimo global permitido cuando el cliente usa la opcion '
            'de monto personalizado en el payment link. '
            'No puede ser inferior a 1,500 COP (estandar Mercado Pago Colombia).'
        ),
    )

    @api.constrains('payment_custom_min_amount')
    def _check_global_min_amount(self):
        for rec in self:
            if rec.payment_custom_min_amount < MERCADO_PAGO_COLOMBIA_MIN:
                _logger.warning(
                    'Intento de configurar monto minimo %.2f inferior al estandar '
                    'Mercado Pago Colombia (%.2f COP). Se usara el minimo permitido.',
                    rec.payment_custom_min_amount,
                    MERCADO_PAGO_COLOMBIA_MIN,
                )