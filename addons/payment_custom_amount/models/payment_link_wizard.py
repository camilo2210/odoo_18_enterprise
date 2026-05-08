# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    allow_custom_amount = fields.Boolean(
        string='Permitir monto personalizado',
        default=False,
        help='Activa la pestaña de monto personalizado en el portal de pago.',
    )
    custom_min_amount = fields.Monetary(
        string='Monto mínimo personalizado',
        currency_field='currency_id',
        default=1500.0,
        help='Monto mínimo aceptado cuando el cliente usa la opción de monto personalizado.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_id = self.env.context.get('active_id')
        res_model = self.env.context.get('active_model')
        if res_id and res_model:
            try:
                record = self.env[res_model].browse(res_id)
                partner = getattr(record, 'partner_id', False)
                if partner:
                    commercial = partner.commercial_partner_id
                    res['allow_custom_amount'] = commercial.allow_custom_payment_amount
                    res['custom_min_amount'] = commercial.custom_payment_min_amount
                    _logger.info(
                        'PaymentLinkWizard: partner=%s allow_custom=%s min=%.2f',
                        commercial.name,
                        res.get('allow_custom_amount'),
                        res.get('custom_min_amount', 0),
                    )
            except Exception as e:
                _logger.warning('PaymentLinkWizard default_get error: %s', str(e))
        return res

    def _get_payment_link_url(self):
        """Extiende la URL del payment link con parámetros de monto personalizado."""
        url = super()._get_payment_link_url()
        if self.allow_custom_amount:
            import urllib.parse
            params = {
                'allow_custom': '1',
                'min_amount': str(self.custom_min_amount),
            }
            separator = '&' if '?' in url else '?'
            url = url + separator + urllib.parse.urlencode(params)
            _logger.info('PaymentLink URL extendida con parámetros de monto personalizado')
        return url