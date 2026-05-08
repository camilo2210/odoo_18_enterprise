# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    allow_custom_payment_amount = fields.Boolean(
        string='Permitir monto personalizado en Payment Link',
        default=False,
        help=(
            'Si está activo, el cliente podrá ingresar un monto '
            'personalizado inferior al total de la factura en el portal de pago.'
        ),
    )
    custom_payment_min_amount = fields.Monetary(
        string='Monto mínimo de pago personalizado',
        currency_field='currency_id',
        default=1500.0,
        help=(
            'Monto mínimo permitido para pagos personalizados. '
            'Por defecto 1,500 COP (mínimo Mercado Pago Colombia).'
        ),
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
    )

    @api.constrains('custom_payment_min_amount')
    def _check_min_amount(self):
        for record in self:
            if record.allow_custom_payment_amount and record.custom_payment_min_amount < 1500.0:
                _logger.warning(
                    'Partner %s tiene monto mínimo %.2f menor al estándar de Mercado Pago Colombia (1500 COP)',
                    record.name,
                    record.custom_payment_min_amount,
                )