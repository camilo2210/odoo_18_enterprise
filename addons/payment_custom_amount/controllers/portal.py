# -*- coding: utf-8 -*-
import logging
from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.account_payment.controllers.payment import PaymentPortal
from odoo.http import request


_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class PaymentCustomAmountPortal(PaymentPortal):

    def invoice_transaction(self, invoice_id, access_token, **kwargs):
        """Override to validate and audit custom amounts coming from the portal.

        The custom amount arrives as ``kwargs['amount']`` because
        ``_prepareTransactionRouteParams()`` (patched in JS) already sets
        the ``amount`` key in the JSON-RPC body.

        This override:
        1. Validates the custom amount against the invoice residual and
           the configured minimum.
        2. Creates an audit record in ``payment.custom.transaction``.
        3. Delegates to ``super()`` which calls ``_create_transaction()``
           with the (possibly overridden) ``amount`` — so the
           ``payment.transaction`` record is created with the correct
           amount in the DB.  Mercado Pago then reads ``self.amount``
           from the DB to build its JSON payload.
        """
        raw_amount = kwargs.get('amount')

        _logger.info(
            ">>> [PORTAL] invoice_transaction: invoice_id=%s, amount=%s",
            invoice_id, raw_amount,
        )

        if raw_amount is not None:
            try:
                amount_float = float(raw_amount)
                invoice = request.env['account.move'].sudo().browse(invoice_id)

                if invoice.exists() and amount_float > 0:
                    # Determine payment type for the audit record
                    if abs(amount_float - invoice.amount_residual) < 0.01:
                        payment_type = 'full'
                    elif amount_float < invoice.amount_residual:
                        payment_type = 'custom'
                    else:
                        payment_type = 'full'

                    # Validate minimum
                    min_amount = invoice.custom_payment_min_amount or MERCADO_PAGO_COLOMBIA_MIN
                    if amount_float < min_amount:
                        raise ValidationError(
                            _('El monto %.2f es inferior al mínimo permitido (%.2f COP).')
                            % (amount_float, min_amount)
                        )

                    # Validate maximum
                    if amount_float > invoice.amount_residual:
                        raise ValidationError(
                            _('El monto %.2f supera el saldo de la factura (%.2f).')
                            % (amount_float, invoice.amount_residual)
                        )

                    # Create audit record
                    try:
                        request.env['payment.custom.transaction'].sudo().create({
                            'reference': invoice.name or 'N/A',
                            'partner_id': invoice.partner_id.id,
                            'move_id': invoice.id,
                            'invoice_total': invoice.amount_residual,
                            'requested_amount': amount_float,
                            'payment_type': payment_type,
                            'currency_id': invoice.currency_id.id,
                            'state': 'validated',
                        })
                        _logger.info(
                            ">>> [PORTAL] ✅ Audit record created: %.2f %s (%s)",
                            amount_float, invoice.currency_id.name, payment_type,
                        )
                    except Exception as e:
                        _logger.error(">>> [PORTAL] ❌ Error creating audit record: %s", e)

                    _logger.info(
                        ">>> [PORTAL] ✅ Custom amount validated: %.2f (residual: %.2f)",
                        amount_float, invoice.amount_residual,
                    )

            except (ValueError, TypeError) as e:
                _logger.error(">>> [PORTAL] ❌ Invalid amount value: %s", e)
            except ValidationError:
                raise
            except Exception as e:
                _logger.error(">>> [PORTAL] ❌ Unexpected error: %s", e)

        return super().invoice_transaction(invoice_id, access_token, **kwargs)