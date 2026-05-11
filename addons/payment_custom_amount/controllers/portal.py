# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.addons.account_payment.controllers.portal import PortalAccount

_logger = logging.getLogger(__name__)


class PaymentCustomAmountPortal(PortalAccount):

    @http.route(
        ['/invoice/transaction/<int:invoice_id>'],  # ← ruta exacta que aparece en el log
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        _logger.info(
            ">>> [PORTAL] invoice_transaction interceptado: invoice_id=%s, kwargs keys=%s",
            invoice_id,
            list(kwargs.keys()),
        )

        custom_amount = kwargs.get('custom_payment_amount')
        custom_type = kwargs.get('custom_payment_type')

        _logger.info(
            ">>> [PORTAL] custom_type=%s, custom_amount=%s",
            custom_type,
            custom_amount,
        )

        if custom_type == 'custom' and custom_amount:
            try:
                amount_float = float(custom_amount)

                # Fix ACL: usar sudo() para leer la factura
                invoice = request.env['account.move'].sudo().browse(invoice_id)

                if amount_float <= 0:
                    raise ValueError("El monto debe ser mayor a 0")

                if amount_float > invoice.amount_residual:
                    _logger.warning(
                        ">>> [PORTAL] Monto %.2f supera residual %.2f, ajustando",
                        amount_float, invoice.amount_residual,
                    )
                    amount_float = invoice.amount_residual

                # Guardar en sesión ANTES de llamar al super()
                request.session['custom_payment_amount'] = amount_float
                _logger.info(
                    ">>> [PORTAL] ✅ Monto guardado en sesión: %.2f", amount_float
                )

            except (ValueError, TypeError) as e:
                _logger.error(">>> [PORTAL] ❌ Error procesando monto: %s", e)
                request.session.pop('custom_payment_amount', None)

        else:
            # Si no es pago parcial, limpiar sesión por si quedó algo anterior
            request.session.pop('custom_payment_amount', None)
            _logger.info(">>> [PORTAL] Pago total — sesión limpia")

        return super().invoice_transaction(invoice_id, access_token, **kwargs)