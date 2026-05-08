# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    allow_custom_payment_amount = fields.Boolean(
        string='Permitir monto personalizado',
        compute='_compute_allow_custom_payment_amount',
        store=True,
        help='Heredado del contacto: indica si se permite pago por monto personalizado.',
    )
    custom_payment_min_amount = fields.Monetary(
        string='Monto mínimo pago personalizado',
        compute='_compute_allow_custom_payment_amount',
        store=True,
        currency_field='currency_id',
        help='Monto mínimo permitido para pagos personalizados en esta factura.',
    )

    @api.depends(
        'partner_id',
        'partner_id.allow_custom_payment_amount',
        'partner_id.custom_payment_min_amount',
    )
    def _compute_allow_custom_payment_amount(self):
        for move in self:
            partner = move.partner_id.commercial_partner_id
            if partner:
                move.allow_custom_payment_amount = partner.allow_custom_payment_amount
                move.custom_payment_min_amount = partner.custom_payment_min_amount
            else:
                move.allow_custom_payment_amount = False
                move.custom_payment_min_amount = 1500.0
            _logger.info(
                'Factura %s: allow_custom=%s, min_amount=%.2f',
                move.name,
                move.allow_custom_payment_amount,
                move.custom_payment_min_amount,
            )