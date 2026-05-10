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

    custom_payment_min_amount = fields.Float(
        string='Monto mínimo pago personalizado',
        compute='_compute_custom_min_amount',
        digits=(16, 2),
        # Sin store=True: se calcula en tiempo real desde ir.config_parameter
        # No necesita columna en BD ni migración
    )

    @api.depends('partner_id', 'partner_id.allow_custom_payment_amount')
    def _compute_allow_custom_payment_amount(self):
        for move in self:
            try:
                partner = move.partner_id.commercial_partner_id
                move.allow_custom_payment_amount = (
                    partner.allow_custom_payment_amount if partner else False
                )
            except Exception as e:
                _logger.error(
                    'Error computando allow_custom en move %s: %s', move.id, str(e)
                )
                move.allow_custom_payment_amount = False

    def _compute_custom_min_amount(self):
        """
        Calcula el monto mínimo en tiempo real desde ir.config_parameter.
        Sin store=True para evitar columna en BD y conflictos de migración.
        """
        min_value = self._get_custom_min_amount()
        for move in self:
            move.custom_payment_min_amount = min_value

    def _get_custom_min_amount(self):
        """Devuelve el monto mínimo global configurado en Ajustes."""
        try:
            value = float(
                self.env['ir.config_parameter'].sudo().get_param(
                    'payment_custom_amount.min_amount',
                    default=str(MERCADO_PAGO_COLOMBIA_MIN),
                )
            )
            return max(value, MERCADO_PAGO_COLOMBIA_MIN)
        except Exception as e:
            _logger.warning('Error leyendo monto mínimo global: %s', str(e))
            return MERCADO_PAGO_COLOMBIA_MIN