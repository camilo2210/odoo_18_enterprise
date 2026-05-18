# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PaymentTransactionCustomAmount(models.Model):
    _inherit = 'payment.transaction'

    # No override of _get_processing_values needed.
    #
    # The custom amount is injected at the JS level via
    # _prepareTransactionRouteParams(), which sends the correct `amount`
    # to the controller's _create_transaction().  The transaction is
    # created in the DB with self.amount = custom_amount, so every
    # provider (including Mercado Pago) reads it correctly.