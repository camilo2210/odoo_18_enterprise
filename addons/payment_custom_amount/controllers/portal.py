# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


def _get_global_min_amount(env):
    """Lee el monto mínimo global desde ir.config_parameter."""
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
    """
    Hereda PaymentPortal para interceptar payment_pay e inyectar
    allow_custom_amount y custom_min_amount al template.
    El flujo /my/invoices/<id> se maneja exclusivamente desde el XML
    mediante t-set — no se necesita override del controlador.
    """

    @http.route()
    def payment_pay(self, *args, **kwargs):
        """
        Override del controlador principal de pago.
        Cubre el flujo de payment link directo (no desde /my/invoices).
        """
        response = super().payment_pay(*args, **kwargs)
        try:
            if hasattr(response, 'qcontext'):
                self._inject_custom_amount_vars(response.qcontext, kwargs)
            elif isinstance(response, dict):
                self._inject_custom_amount_vars(response, kwargs)
        except Exception as e:
            _logger.exception(
                'Error inyectando variables en payment_pay: %s', str(e)
            )
        return response

    def _inject_custom_amount_vars(self, values, kwargs):
        """
        Resuelve el partner e inyecta allow_custom_amount y custom_min_amount
        en el dict del template QWeb.
        """
        allow_custom = False
        min_amount = _get_global_min_amount(request.env)

        # Fuente 1: partner_id directo en kwargs o values
        partner_id = kwargs.get('partner_id') or values.get('partner_id')

        # Fuente 2: invoice_id (flujo correo de factura)
        invoice_id = kwargs.get('invoice_id') or values.get('invoice_id')
        if not partner_id and invoice_id:
            try:
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                if invoice.exists():
                    partner_id = invoice.partner_id.id
            except Exception as e:
                _logger.warning(
                    'No se pudo resolver partner desde invoice_id: %s', str(e)
                )

        # Fuente 3: access_token
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
                    _logger.warning(
                        'No se pudo resolver partner desde access_token: %s', str(e)
                    )

        # Resolver allow_custom desde el partner encontrado
        if partner_id:
            try:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                commercial = partner.commercial_partner_id
                allow_custom = commercial.allow_custom_payment_amount
                _logger.info(
                    'payment_pay: partner=%s allow_custom=%s min=%.2f',
                    commercial.name, allow_custom, min_amount,
                )
            except Exception as e:
                _logger.warning(
                    'Error resolviendo partner %s: %s', partner_id, str(e)
                )

        values['allow_custom_amount'] = allow_custom
        values['custom_min_amount'] = min_amount

        # Sobrescribir si el payment link manual trae allow_custom=1 en URL
        if not allow_custom:
            url_allow = kwargs.get('allow_custom', '0')
            if str(url_allow) == '1':
                values['allow_custom_amount'] = True
                url_min = kwargs.get('min_amount')
                if url_min:
                    try:
                        values['custom_min_amount'] = max(
                            float(url_min), MERCADO_PAGO_COLOMBIA_MIN
                        )
                    except (TypeError, ValueError):
                        pass

    @http.route(
        '/payment/custom/validate_amount',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def validate_custom_amount(self, amount, invoice_id=None, **kwargs):
        """Valida el monto personalizado vía AJAX."""
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
                    '(estándar Mercado Pago Colombia).',
                    min_amount,
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
                                'El monto %.2f supera el saldo pendiente (%.2f).',
                                amount, max_amount,
                            ),
                        }
            except Exception as e:
                _logger.warning(
                    'Error al validar monto contra factura %s: %s', invoice_id, str(e)
                )

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
        """Crea registro de auditoría para transacciones con monto personalizado."""
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