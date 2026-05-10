# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.payment import utils as payment_utils

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

    # ── Override del endpoint que crea la payment.transaction ────────────────
    @http.route(
        '/invoice/transaction/<int:invoice_id>',
        type='json',
        auth='public',
    )
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """
        Override del endpoint nativo de account_payment.
        Intercepta el monto personalizado guardado en sesión y lo aplica
        ANTES de que se cree la payment.transaction.
        """
        # Recuperar monto personalizado de la sesión
        custom_amount = request.session.pop('custom_payment_amount', None)

        if custom_amount:
            try:
                custom_amount = float(custom_amount)
                min_amount = _get_global_min_amount(request.env)

                # Validar rango
                invoice = request.env['account.move'].sudo().browse(invoice_id)
                max_amount = invoice.amount_residual if invoice.exists() else 0

                if custom_amount < min_amount:
                    _logger.warning(
                        'Monto personalizado %.2f menor al mínimo %.2f, usando total',
                        custom_amount, min_amount,
                    )
                    custom_amount = None
                elif max_amount > 0 and custom_amount > max_amount:
                    _logger.warning(
                        'Monto personalizado %.2f mayor al saldo %.2f, usando total',
                        custom_amount, max_amount,
                    )
                    custom_amount = None
                else:
                    _logger.info(
                        'Aplicando monto personalizado %.2f para factura %s',
                        custom_amount, invoice_id,
                    )
                    # Inyectar el monto en kwargs para que el super() lo use
                    kwargs['amount'] = custom_amount

            except (TypeError, ValueError) as e:
                _logger.warning('Monto personalizado inválido en sesión: %s', str(e))
                custom_amount = None

        # Llamar al controlador nativo con el monto (modificado o no)
        from odoo.addons.account_payment.controllers.portal import PortalAccount
        portal = PortalAccount()
        return portal.invoice_transaction(invoice_id, access_token, **kwargs)

    # ── Guardar monto en sesión desde JS ─────────────────────────────────────
    @http.route(
        '/payment/custom/save_session_amount',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def save_session_amount(self, amount, **kwargs):
        """Guarda el monto personalizado en sesión antes del submit."""
        try:
            amount = float(amount)
            min_amount = _get_global_min_amount(request.env)
            if amount >= min_amount:
                request.session['custom_payment_amount'] = amount
                _logger.info('Monto personalizado %.2f guardado en sesión', amount)
                return {'success': True, 'amount': amount}
            else:
                return {
                    'success': False,
                    'message': 'Monto inferior al mínimo permitido (%.2f)' % min_amount,
                }
        except (TypeError, ValueError) as e:
            _logger.warning('Error guardando monto en sesión: %s', str(e))
            return {'success': False, 'message': str(e)}

    # ── Validación AJAX ───────────────────────────────────────────────────────
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
                'message': _(
                    'El monto mínimo permitido es %.2f COP '
                    '(estándar Mercado Pago Colombia).', min_amount,
                ),
            }

        if invoice_id:
            try:
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                if invoice.exists():
                    max_amount = invoice.amount_residual
                    if amount > max_amount:
                        return {
                            'valid': False,
                            'message': _(
                                'El monto %.2f supera el saldo pendiente (%.2f).',
                                amount, max_amount,
                            ),
                        }
            except Exception as e:
                _logger.warning('Error validando contra factura %s: %s', invoice_id, str(e))

        return {'valid': True, 'message': _('Monto válido.'), 'amount': amount}

    # ── Registro de auditoría ─────────────────────────────────────────────────
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
            values = {
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
            }
            tx = request.env['payment.custom.transaction'].sudo().create(values)
            _logger.info('Auditoría creada: id=%s ref=%s', tx.id, tx.reference)
            return {'success': True, 'record_id': tx.id}
        except Exception as e:
            _logger.exception('Error creando registro de auditoría: %s', str(e))
            return {'success': False, 'message': str(e)}