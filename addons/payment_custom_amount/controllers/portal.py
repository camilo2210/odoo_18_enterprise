# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request

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


class PaymentCustomAmountPortal(http.Controller):
    """
    Controller propio del módulo.
    NO hereda PortalAccount para no interferir con la ruta
    /invoice/transaction/ ni romper la validación CSRF nativa de Odoo.
    El monto personalizado lo inyecta window.fetch (JS) directamente
    en el body antes de que salga la petición al servidor.
    """

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
        """ Ruta de auditoría para registrar el intento de pago personalizado """
        try:
            seq = request.env['ir.sequence'].sudo().next_by_code('payment.custom.transaction')
            tx = request.env['payment.custom.transaction'].sudo().create({
                'reference': reference or ('CUSTOM-%s' % seq),
                'partner_id': int(partner_id) if partner_id else False,
                'move_id': int(invoice_id) if invoice_id else False,
                'invoice_total': float(invoice_total),
                'requested_amount': float(requested_amount),
                'payment_type': payment_type,
                'provider_code': provider_code or '',
                'currency_id': int(currency_id) if currency_id else request.env.company.currency_id.id,
                'state': 'pending',
            })
            return {'success': True, 'record_id': tx.id}
        except Exception as e:
            _logger.error("Error en auditoría: %s", str(e))
            return {'success': False, 'error': str(e)}


class PaymentCustomAmountValidation(http.Controller):
    """
    Endpoint AJAX para validar el monto personalizado en tiempo real
    desde el portal, antes de que el cliente confirme el pago.
    """

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
                        'message': _(
                            'Supera el saldo pendiente (%.2f).',
                            inv.amount_residual,
                        ),
                    }
            except Exception as e:
                _logger.warning('Error validando contra factura: %s', str(e))

        return {'valid': True, 'message': _('Monto válido.'), 'amount': amount}
