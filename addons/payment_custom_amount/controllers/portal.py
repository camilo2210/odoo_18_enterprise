# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal

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


class PaymentCustomAmountPortal(PaymentPortal):

    @http.route()
    def payment_pay(self, *args, **kwargs):
        response = super().payment_pay(*args, **kwargs)
        try:
            qcontext = getattr(response, 'qcontext', None)
            if isinstance(qcontext, dict):
                self._inject_custom_amount_vars(qcontext, kwargs)
        except Exception as e:
            _logger.exception('Error inyectando vars en payment_pay: %s', str(e))
        return response

    def _inject_custom_amount_vars(self, values, kwargs):
        allow_custom = False
        min_amount = _get_global_min_amount(request.env)
        partner_id = kwargs.get('partner_id') or values.get('partner_id')

        if not partner_id:
            access_token = kwargs.get('access_token', '')
            if access_token:
                try:
                    invoice = request.env['account.move'].sudo().search(
                        [('access_token', '=', access_token)], limit=1
                    )
                    if invoice:
                        partner_id = invoice.partner_id.id
                except Exception as e:
                    _logger.warning('Error resolviendo partner: %s', str(e))

        if partner_id:
            try:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                allow_custom = partner.commercial_partner_id.allow_custom_payment_amount
            except Exception as e:
                _logger.warning('Error leyendo partner %s: %s', partner_id, str(e))

        values['allow_custom_amount'] = allow_custom
        values['custom_min_amount'] = min_amount

    @http.route(
        '/payment/custom/save_session_amount',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def save_session_amount(self, amount, **kwargs):
        try:
            amount = float(amount)
            min_amount = _get_global_min_amount(request.env)
            if amount >= min_amount:
                request.session['custom_payment_amount'] = amount
                _logger.info('Monto %.2f guardado en sesión', amount)
                return {'success': True, 'amount': amount}
            return {
                'success': False,
                'message': 'Monto inferior al mínimo (%.2f COP)' % min_amount,
            }
        except (TypeError, ValueError) as e:
            _logger.warning('Error guardando monto en sesión: %s', str(e))
            return {'success': False, 'message': str(e)}

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
            return {'valid': False, 'message': _('Monto no válido.')}

        min_amount = _get_global_min_amount(request.env)
        if amount < min_amount:
            return {'valid': False, 'message': _('Monto mínimo: %.2f COP.', min_amount)}

        if invoice_id:
            try:
                inv = request.env['account.move'].sudo().browse(int(invoice_id))
                if inv.exists() and amount > inv.amount_residual:
                    return {'valid': False, 'message': _('Supera el saldo (%.2f).', inv.amount_residual)}
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