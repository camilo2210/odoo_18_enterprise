# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # pgm_operation_type = fields.Selection(
    #     selection=[
    #         ('', 'Empty'),
    #         ('capex', 'CAPEX'),
    #         ('opex', 'OPEX'),
    #     ],
    #     string="Operation Type",
    #     help="Operational classification of the purchase: CAPEX or OPEX.",
    # )

    pgm_purchase_type = fields.Selection(
        selection=[
            ('', 'Empty'),
            ('derechos_uso', 'Rights of use'),
            ('propiedades_inversion', 'Investment Properties'),
            ('ppe', 'PPE'),
            ('intangibles', 'Intangible assets'),
            ('activos_biologicos', 'Biological assets'),
            ('gastos_anticipados', 'Prepaid expenses'),
        ],
        string="Purchase Type",
        help="Accounting classification of the purchased good/service.",
    )
