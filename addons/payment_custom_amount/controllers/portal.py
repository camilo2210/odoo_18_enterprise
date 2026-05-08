# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class PaymentCustomAmountPortal(http.Controller):

    @http.route(
        '/payment/custom/validate_amount',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def validate_custom_amount(self, amount, invoice_id=None, **kwargs):
        """
        Valida el monto personalizado ingresado por el cliente vía AJAX.
        Retorna dict con {valid: bool, message: str, amount: float}
        """
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {'valid': False, 'message': _('El monto ingresado no es válido.')}

        if amount < MERCADO_PAGO_COLOMBIA_MIN:
            return {
                'valid': False,
                'message': _(
                    'El monto mínimo permitido es %.2f COP '
                    '(estándar Mercado Pago Colombia).',
                    MERCADO_PAGO_COLOMBIA_MIN,
                ),
            }

        if invoice_id:
            try:
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                if invoice.exists() and invoice.move_type in ('out_invoice', 'out_refund'):
                    max_amount = invoice.amount_residual
                    if amount > max_amount:
                        return {
                            'valid': False,
                            'message': _(
                                'El monto %.2f supera el saldo pendiente '
                                'de la factura (%.2f).',
                                amount, max_amount,
                            ),
                        }
                    partner = invoice.partner_id.commercial_partner_id
                    partner_min = (
                        partner.custom_payment_min_amount
                        if partner else MERCADO_PAGO_COLOMBIA_MIN
                    )
                    effective_min = max(MERCADO_PAGO_COLOMBIA_MIN, partner_min)
                    if amount < effective_min:
                        return {
                            'valid': False,
                            'message': _(
                                'El monto mínimo configurado para este cliente es %.2f.',
                                effective_min,
                            ),
                        }
            except Exception as e:
                _logger.warning(
                    'Error al validar monto contra factura %s: %s', invoice_id, str(e)
                )

        _logger.info('Monto personalizado %.2f validado correctamente.', amount)
        return {'valid': True, 'message': _('Monto válido.'), 'amount': amount}

    @http.route(
        '/payment/custom/record_transaction',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def record_custom_transaction(
        self,
        reference,
        partner_id,
        invoice_id=None,
        invoice_total=0.0,
        requested_amount=0.0,
        payment_type='custom',
        provider_code='',
        currency_id=None,
        **kwargs
    ):
        """
        Crea un registro de auditoría para transacciones con monto personalizado.
        """
        try:
            seq = request.env['ir.sequence'].sudo().next_by_code(
                'payment.custom.transaction'
            )
            values = {
                'reference': reference or ('CUSTOM-%s' % seq),
                'partner_id': int(partner_id) if partner_id else False,
                'move_id': int(invoice_id) if invoice_id else False,
                'invoice_total': float(invoice_total),
                'requested_amount': float(requested_amount),
                'payment_type': payment_type,
                'provider_code': provider_code or '',
                'currency_id': int(currency_id) if currency_id
                               else request.env.company.currency_id.id,
                'state': 'pending',
            }
            tx_record = request.env['payment.custom.transaction'].sudo().create(values)
            _logger.info(
                'Registro creado: id=%s ref=%s amount=%.2f',
                tx_record.id, tx_record.reference, tx_record.requested_amount,
            )
            return {'success': True, 'record_id': tx_record.id}
        except Exception as e:
            _logger.exception(
                'Error al crear registro de transacción personalizada: %s', str(e)
            )
            return {'success': False, 'message': str(e)}