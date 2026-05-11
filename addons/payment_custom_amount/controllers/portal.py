# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
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
        personalizado. Se guarda en sesión para que payment.transaction lo procese.
        """
        custom_amount = kwargs.get('custom_payment_amount')
        custom_type = kwargs.get('custom_payment_type')

        if custom_type == 'custom' and custom_amount:
            try:
                amount_float = float(custom_amount)
                min_amt = _get_global_min_amount(request.env)
                
                # Validación de seguridad en servidor
                if amount_float >= min_amt:
                    # PASO CLAVE: Guardar en sesión para el modelo payment.transaction
                    request.session['custom_payment_amount'] = amount_float
                    # Forzamos el monto en kwargs para el flujo estándar de Odoo
                    kwargs['amount'] = amount_float
                    _logger.info("Monto personalizado %.2f inyectado en sesión", amount_float)
                else:
                    _logger.warning("Monto %.2f por debajo del mínimo %.2f", amount_float, min_amt)
            except (ValueError, TypeError):
                _logger.error("Monto personalizado inválido recibido: %s", custom_amount)

        return super().invoice_transaction(invoice_id, access_token, **kwargs)

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