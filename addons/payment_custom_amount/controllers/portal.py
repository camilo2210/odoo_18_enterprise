# -*- coding: utf-8 -*-
import logging
from odoo.addons.account_payment.controllers.payment import InvoicePaymentController
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymentCustomAmountPortal(InvoicePaymentController):

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

                invoice = request.env['account.move'].sudo().browse(invoice_id)

                if amount_float <= 0:
                    raise ValueError("Monto debe ser mayor a 0")

                if amount_float > invoice.amount_residual:
                    amount_float = invoice.amount_residual
                    _logger.warning(">>> [PORTAL] Monto ajustado al residual: %.2f", amount_float)

                request.session['custom_payment_amount'] = amount_float
                _logger.info(">>> [PORTAL] ✅ Sesión guardada: %.2f", amount_float)

            except (ValueError, TypeError) as e:
                _logger.error(">>> [PORTAL] ❌ Error: %s", e)
                request.session.pop('custom_payment_amount', None)
        else:
            request.session.pop('custom_payment_amount', None)
            _logger.info(">>> [PORTAL] Pago total — sesión limpia")

        return super().invoice_transaction(invoice_id, access_token, **kwargs)