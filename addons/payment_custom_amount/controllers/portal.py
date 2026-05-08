# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentPortal

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


def _get_global_min_amount(env):
    """Lee el monto minimo global desde ir.config_parameter."""
    try:
        value = float(
            env['ir.config_parameter'].sudo().get_param(
                'payment_custom_amount.min_amount',
                default=str(MERCADO_PAGO_COLOMBIA_MIN),
            )
        )
        return max(value, MERCADO_PAGO_COLOMBIA_MIN)
    except Exception as e:
        _logger.warning('Error leyendo monto minimo global: %s', str(e))
        return MERCADO_PAGO_COLOMBIA_MIN


class PaymentCustomAmountPortal(PaymentPortal):
    """
    Hereda PaymentPortal para interceptar payment_pay e inyectar
    las variables allow_custom_amount y custom_min_amount al template,
    tanto cuando viene del payment link manual como del correo de factura.
    """

    @http.route()
    def payment_pay(self, *args, **kwargs):
        """
        Override del controlador principal de pago.
        Inyecta allow_custom_amount y custom_min_amount en la respuesta
        del template para que el QWeb los tenga disponibles.
        """
        # Llamar al metodo original para obtener la respuesta/valores base
        response = super().payment_pay(*args, **kwargs)

        try:
            # La respuesta puede ser un Response de werkzeug con qcontext
            # o un dict de valores (segun la version de Odoo)
            if hasattr(response, 'qcontext'):
                self._inject_custom_amount_vars(response.qcontext, kwargs)
            elif isinstance(response, dict):
                self._inject_custom_amount_vars(response, kwargs)
        except Exception as e:
            _logger.exception(
                'Error inyectando variables de monto personalizado en payment_pay: %s',
                str(e),
            )

        return response

    def _inject_custom_amount_vars(self, values, kwargs):
        """
        Inyecta allow_custom_amount y custom_min_amount en el dict de valores
        del template QWeb. Resuelve el partner desde el contexto disponible.
        """
        allow_custom = False
        min_amount = _get_global_min_amount(request.env)

        # Intentar resolver el partner desde distintas fuentes
        partner_id = (
            kwargs.get('partner_id')
            or values.get('partner_id')
        )

        # Intentar desde invoice_id (flujo correo de factura)
        invoice_id = kwargs.get('invoice_id') or values.get('invoice_id')
        if not partner_id and invoice_id:
            try:
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                if invoice.exists():
                    partner_id = invoice.partner_id.id
            except Exception as e:
                _logger.warning('No se pudo resolver partner desde invoice_id: %s', str(e))

        # Intentar desde access_token buscando la transaccion/factura relacionada
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
                    'Inyectando contexto de pago: partner=%s allow_custom=%s min=%.2f',
                    commercial.name, allow_custom, min_amount,
                )
            except Exception as e:
                _logger.warning('Error resolviendo partner %s: %s', partner_id, str(e))

        # Inyectar en el contexto del template
        values['allow_custom_amount'] = allow_custom
        values['custom_min_amount'] = min_amount

        # Leer allow_custom desde parametros de URL (viene del payment link manual)
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
        """Valida el monto personalizado via AJAX."""
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {'valid': False, 'message': _('El monto ingresado no es valido.')}

        min_amount = _get_global_min_amount(request.env)

        if amount < min_amount:
            return {
                'valid': False,
                'message': _(
                    'El monto minimo permitido es %.2f COP '
                    '(estandar Mercado Pago Colombia).',
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

        return {'valid': True, 'message': _('Monto valido.'), 'amount': amount}

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
        """Crea registro de auditoria para transacciones con monto personalizado."""
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
                'Error al crear registro de transaccion personalizada: %s', str(e)
            )
            return {'success': False, 'message': str(e)}
    
    @http.route('/my/invoices/<int:invoice_id>', type='http', auth='public', website=True)
    def portal_invoice_page(self, invoice_id, **kwargs):
        """
        Override del portal de facturas para inyectar variables de monto
        personalizado en el contexto de la pagina antes de renderizarla.
        """
        # Llamar al controlador padre de account_payment
        from odoo.addons.account_payment.controllers.portal import (
            PortalAccount as BasePortalAccount
        )
        response = super(PaymentCustomAmountPortal, self).portal_invoice_page(
            invoice_id, **kwargs
        )

        try:
            if hasattr(response, 'qcontext'):
                invoice = request.env['account.move'].sudo().browse(invoice_id)
                if invoice.exists():
                    partner = invoice.partner_id.commercial_partner_id
                    min_amount = _get_global_min_amount(request.env)
                    response.qcontext['allow_custom_amount'] = (
                        partner.allow_custom_payment_amount
                    )
                    response.qcontext['custom_min_amount'] = min_amount
                    _logger.info(
                        'Portal factura %s: allow_custom=%s min=%.2f',
                        invoice.name,
                        partner.allow_custom_payment_amount,
                        min_amount,
                    )
        except Exception as e:
            _logger.exception(
                'Error inyectando vars en portal_invoice_page id=%s: %s',
                invoice_id, str(e),
            )

        return response