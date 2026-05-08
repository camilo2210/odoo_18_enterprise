# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

MERCADO_PAGO_COLOMBIA_MIN = 1500.0


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    allow_custom_amount = fields.Boolean(
        string='Permitir monto personalizado',
        default=False,
    )
    custom_min_amount = fields.Float(
        string='Monto minimo personalizado (COP)',
        default=MERCADO_PAGO_COLOMBIA_MIN,
        help='Se hereda de la configuracion global. Minimo absoluto: 1,500 COP.',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_id = self.env.context.get('active_id')
        res_model = self.env.context.get('active_model')

        # Leer monto minimo global
        try:
            global_min = float(
                self.env['ir.config_parameter'].sudo().get_param(
                    'payment_custom_amount.min_amount',
                    default=str(MERCADO_PAGO_COLOMBIA_MIN),
                )
            )
            res['custom_min_amount'] = max(global_min, MERCADO_PAGO_COLOMBIA_MIN)
        except Exception as e:
            _logger.warning('Error leyendo config global en wizard: %s', str(e))
            res['custom_min_amount'] = MERCADO_PAGO_COLOMBIA_MIN

        # Heredar allow_custom del partner de la factura/pedido
        if res_id and res_model:
            try:
                record = self.env[res_model].browse(res_id)
                partner = getattr(record, 'partner_id', False)
                if partner:
                    commercial = partner.commercial_partner_id
                    res['allow_custom_amount'] = commercial.allow_custom_payment_amount
                    _logger.info(
                        'PaymentLinkWizard: partner=%s allow_custom=%s',
                        commercial.name,
                        res.get('allow_custom_amount'),
                    )
            except Exception as e:
                _logger.warning('PaymentLinkWizard default_get error: %s', str(e))
        return res

    def _get_payment_link_url(self):
        """Extiende la URL con parametros de monto personalizado."""
        url = super()._get_payment_link_url()
        if self.allow_custom_amount:
            import urllib.parse
            params = {
                'allow_custom': '1',
                'min_amount': str(self.custom_min_amount),
            }
            separator = '&' if '?' in url else '?'
            url = url + separator + urllib.parse.urlencode(params)
            _logger.info('PaymentLink URL extendida con parametros de monto personalizado')
        return url