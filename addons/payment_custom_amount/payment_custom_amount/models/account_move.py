# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class AccountMove(models.Model):
    _inherit = 'account.move'

    allow_custom_payment_amount = fields.Boolean(
        string='Permitir monto personalizado',
        compute='_compute_allow_custom_payment_amount',
        store=True,
    )

    @api.depends('partner_id', 'partner_id.allow_custom_payment_amount')
    def _compute_allow_custom_payment_amount(self):
        for move in self:
            partner = move.partner_id.commercial_partner_id
            move.allow_custom_payment_amount = (
                partner.allow_custom_payment_amount if partner else False
            )

    def _get_custom_min_amount(self):
        """Devuelve el monto minimo global configurado en Ajustes."""
        try:
            value = float(
                self.env['ir.config_parameter'].sudo().get_param(
                    'payment_custom_amount.min_amount',
                    default=str(MERCADO_PAGO_COLOMBIA_MIN),
                )
            )
            return max(value, MERCADO_PAGO_COLOMBIA_MIN)
        except Exception as e:
            _logger.warning('Error leyendo monto minimo global: %s', str(e))
            return MERCADO_PAGO_COLOMBIA_MIN