# -*- coding: utf-8 -*-
import logging
from odoo.addons.account_payment.controllers.payment import PaymentPortal
from odoo.http import request


_logger = logging.getLogger(__name__)


class PaymentCustomAmountPortal(PaymentPortal):

    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        _logger.info(
            ">>> [PORTAL] invoice_transaction interceptado: invoice_id=%s, kwargs keys=%s",
            invoice_id,
            list(kwargs.keys()),
        )

        # ── CAMBIO: leer 'amount' que ya viene en kwargs desde el formulario portal ──
        raw_amount = kwargs.get('amount')
        _logger.info(
            ">>> [PORTAL] amount en kwargs: %s (tipo: %s)",
            raw_amount, type(raw_amount)
        )

        if raw_amount is not None:
            try:
                amount_float = float(raw_amount)
                invoice = request.env['account.move'].sudo().browse(invoice_id)

                if 0 < amount_float < invoice.amount_residual:
                    # Pago parcial válido → guardar en sesión
                    request.session['custom_payment_amount'] = amount_float
                    _logger.info(
                        ">>> [PORTAL] ✅ Pago PARCIAL guardado: %.2f (residual: %.2f)",
                        amount_float, invoice.amount_residual
                    )
                else:
                    # Pago total o monto inválido → limpiar sesión
                    request.session.pop('custom_payment_amount', None)
                    _logger.info(
                        ">>> [PORTAL] Pago TOTAL o inválido: %.2f — sesión limpia",
                        amount_float
                    )

            except (ValueError, TypeError) as e:
                _logger.error(">>> [PORTAL] ❌ Error convirtiendo amount: %s", e)
                request.session.pop('custom_payment_amount', None)
        else:
            request.session.pop('custom_payment_amount', None)
            _logger.info(">>> [PORTAL] amount no encontrado en kwargs — sesión limpia")

        return super().invoice_transaction(invoice_id, access_token, **kwargs)