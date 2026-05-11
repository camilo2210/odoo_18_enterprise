# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.addons.account_payment.controllers.portal import PortalAccount

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


def _get_global_min_amount(env):
    try:
        value = float(
            env['ir.config_parameter'].sudo().get_param(
                'payment_custom_amount.min_amount',
                default=str(MERCADO_PAGO_COLOMBIA_MIN),
            )
        )
        return max(value, MERCADO_PAGO_COLOMBIA_MIN)
    except Exception as e:
        _logger.warning('Error leyendo monto mínimo global: %s', str(e))
        return MERCADO_PAGO_COLOMBIA_MIN


class PaymentCustomAmountPortal(PortalAccount):

    @http.route()
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """
        Override de /invoice/transaction/<id> para interceptar el monto
        personalizado enviado como campo oculto desde el formulario del portal.
        El monto se valida y se inyecta en kwargs['amount'] antes de crear la TX.
        """
        custom_amount = kwargs.pop('custom_payment_amount', None)
        custom_type   = kwargs.pop('custom_payment_type', 'full')

        if custom_amount and custom_type == 'custom':
            try:
                custom_amount = float(custom_amount)
                min_amount    = _get_global_min_amount(request.env)

                # Obtener la factura para validar el máximo
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                max_amount = invoice.amount_residual if invoice.exists() else 0

                if custom_amount >= min_amount and (max_amount == 0 or custom_amount <= max_amount):
                    _logger.info(
                        'invoice_transaction: factura=%s monto_personalizado=%.2f '
                        '(original=%.2f) aplicado',
                        invoice_id, custom_amount, kwargs.get('amount', 0),
                    )
                    kwargs['amount'] = custom_amount
                else:
                    _logger.warning(
                        'invoice_transaction: monto_personalizado=%.2f fuera de '
                        'rango [%.2f, %.2f] — ignorado',
                        custom_amount, min_amount, max_amount,
                    )
            except (TypeError, ValueError) as e:
                _logger.warning('invoice_transaction: monto inválido: %s', str(e))

        return super().invoice_transaction(invoice_id, access_token, **kwargs)


class PaymentCustomAmountValidation(http.Controller):

    @http.route(
        '/payment/custom/validate_amount',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def validate_custom_amount(self, amount, invoice_id=None, **kwargs):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {'valid': False, 'message': _('El monto ingresado no es válido.')}

        min_amount = _get_global_min_amount(request.env)
        if amount < min_amount:
            return {
                'valid': False,
                'message': _('El monto mínimo permitido es %.2f COP.', min_amount),
            }

        if invoice_id:
            try:
                inv = request.env['account.move'].sudo().browse(int(invoice_id))
                if inv.exists() and amount > inv.amount_residual:
                    return {
                        'valid': False,
                        'message': _('Supera el saldo pendiente (%.2f).', inv.amount_residual),
                    }
            except Exception as e:
                _logger.warning('Error validando factura: %s', str(e))

        return {'valid': True, 'message': _('Monto válido.'), 'amount': amount}

    @http.route(
        '/payment/custom/record_transaction',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def record_custom_transaction(
        self, reference, partner_id,
        invoice_id=None, invoice_total=0.0,
        requested_amount=0.0, payment_type='custom',
        provider_code='', currency_id=None, **kwargs
    ):
        try:
            seq = request.env['ir.sequence'].sudo().next_by_code(
                'payment.custom.transaction'
            )
            tx = request.env['payment.custom.transaction'].sudo().create({
                'reference': reference or ('CUSTOM-%s' % seq),
                'partner_id': int(partner_id) if partner_id else False,
                'move_id': int(invoice_id) if invoice_id else False,
                'invoice_total': float(invoice_total),
                'requested_amount': float(requested_amount),
                'payment_type': payment_type,
                'provider_code': provider_code or '',
                'currency_id': (
                    int(currency_id) if currency_id
                    else request.env.company.currency_id.id
                ),
                'state': 'pending',
            })
            _logger.info('Auditoría: id=%s ref=%s', tx.id, tx.reference)
            return {'success': True, 'record_id': tx.id}
        except Exception as e:
            _logger.exception('Error en auditoría: %s', str(e))
            return {'success': False, 'message': str(e)}