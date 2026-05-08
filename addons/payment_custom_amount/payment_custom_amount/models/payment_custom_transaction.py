# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class PaymentCustomTransaction(models.Model):
    """
    Registro de auditoría de pagos con monto personalizado.
    Inmutable: solo lectura una vez creado.
    """
    _name = 'payment.custom.transaction'
    _description = 'Registro de Pago con Monto Personalizado'
    _order = 'create_date desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Referencia',
        required=True,
        index=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        index=True,
        ondelete='restrict',
        readonly=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Factura',
        index=True,
        ondelete='set null',
        readonly=True,
    )
    invoice_total = fields.Monetary(
        string='Total Factura',
        currency_field='currency_id',
        readonly=True,
    )
    requested_amount = fields.Monetary(
        string='Monto Solicitado',
        currency_field='currency_id',
        required=True,
        readonly=True,
    )
    payment_type = fields.Selection(
        selection=[
            ('full', 'Total'),
            ('partial', 'Parcial'),
            ('custom', 'Monto Personalizado'),
        ],
        string='Tipo de Pago',
        required=True,
        readonly=True,
    )
    provider_code = fields.Char(
        string='Proveedor',
        readonly=True,
        help='Código del proveedor de pago: mercado_pago, stripe, etc.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pendiente'),
            ('validated', 'Validado'),
            ('rejected', 'Rechazado'),
        ],
        string='Estado',
        default='pending',
        readonly=True,
    )
    validation_error = fields.Text(
        string='Error de Validación',
        readonly=True,
    )
    create_date = fields.Datetime(
        string='Fecha de Solicitud',
        readonly=True,
    )

    @api.constrains('requested_amount', 'invoice_total', 'payment_type')
    def _check_amounts(self):
        for record in self:
            try:
                if record.requested_amount < MERCADO_PAGO_COLOMBIA_MIN:
                    raise ValidationError(
                        _(
                            'El monto %.2f es inferior al mínimo permitido por '
                            'Mercado Pago Colombia (%.2f COP).',
                            record.requested_amount,
                            MERCADO_PAGO_COLOMBIA_MIN,
                        )
                    )
                if record.payment_type == 'custom' and record.invoice_total > 0:
                    if record.requested_amount > record.invoice_total:
                        raise ValidationError(
                            _(
                                'El monto personalizado %.2f no puede superar el '
                                'total de la factura %.2f.',
                                record.requested_amount,
                                record.invoice_total,
                            )
                        )
            except ValidationError:
                raise
            except Exception as e:
                _logger.exception(
                    'Error inesperado al validar montos del registro %s: %s',
                    record.reference, str(e),
                )
                raise

    def action_validate(self):
        for record in self:
            try:
                record.state = 'validated'
                _logger.info('Transacción %s validada manualmente.', record.reference)
            except Exception as e:
                _logger.error('Error al validar transacción %s: %s', record.reference, str(e))

    def action_reject(self):
        for record in self:
            try:
                record.state = 'rejected'
                _logger.warning('Transacción %s rechazada manualmente.', record.reference)
            except Exception as e:
                _logger.error('Error al rechazar transacción %s: %s', record.reference, str(e))