# -*- coding: utf-8 -*-
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    allow_custom_payment_amount = fields.Boolean(
        string='Permitir monto personalizado en Payment Link',
        default=False,
        help=(
            'Si esta activo, el cliente vera una pestana extra en el portal de pago '
            'para ingresar un monto inferior al total. '
            'El monto minimo global se configura en Ajustes > Payment Link.'
        ),
    )