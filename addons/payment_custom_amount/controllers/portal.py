# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.addons.account_payment.controllers.portal import PortalAccount

_logger = logging.getLogger(__name__)


class PaymentCustomAmountPortal(PortalAccount):

    @http.route(
        '/my/invoices/<int:invoice_id>/transaction/<int:provider_id>',
        type='json',
        auth='public',
        website=True,
    )
    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """
        Intercepta la creación de transacción para inyectar monto personalizado.
        El log SIEMPRE debe estar DENTRO del método, nunca a nivel de clase.
        """
        # ← LOG CORRECTO: indentado dentro del método
        _logger.info(
            ">>> [PORTAL] invoice_transaction recibido: "
            "invoice_id=%s, kwargs=%s",
            invoice_id,
            kwargs,
        )

        custom_amount = kwargs.get('custom_payment_amount')
        custom_type = kwargs.get('custom_payment_type')

        if custom_type == 'custom' and custom_amount:
            try:
                amount_float = float(custom_amount)

                # Validar que no supere el residual de la factura
                invoice = request.env['account.move'].sudo().browse(invoice_id)
                if amount_float > invoice.amount_residual:
                    _logger.warning(
                        ">>> [PORTAL] Monto %.2f supera residual %.2f, se usa residual",
                        amount_float,
                        invoice.amount_residual,
                    )
                    amount_float = invoice.amount_residual

                # Guardar en sesión para que _create_transaction lo lea
                request.session['custom_payment_amount'] = amount_float
                _logger.info(
                    ">>> [PORTAL] Monto personalizado guardado en sesión: %.2f",
                    amount_float,
                )

            except (ValueError, TypeError):
                _logger.error(
                    ">>> [PORTAL] Error al convertir monto: %s", custom_amount
                )
                # Limpiar sesión si hubo error
                request.session.pop('custom_payment_amount', None)

        return super().invoice_transaction(invoice_id, access_token, **kwargs)