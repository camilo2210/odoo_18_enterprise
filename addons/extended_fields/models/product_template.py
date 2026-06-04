# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pgm_description = fields.Text(
        string="Description",
        help="Description of the product (multiline).",
    )

    pgm_creation_request_date = fields.Date(
        string="Creation Request Date",
        help="Date when the product creation request was made.",
    )

    pgm_material_type = fields.Selection(
        selection=[
            ('sistema_basico_equipo_movil', 'Basic system mobile equipment'),
            ('rodamientos_sellos', 'Bearings and seals'),
            ('repuesto_mecanico_planta', 'Plant mechanical spare parts'),
            ('repuestos_electricos', 'Electrical spare parts'),
            ('repuestos_electronicos', 'Electronic spare parts'),
            ('material_empaque', 'Packaging material'),
            ('filtros', 'Filters'),
            ('ferreteria', 'Hardware'),
            ('combustibles_lubricantes', 'Fuels/Lubricants'),
            ('articulos_generales', 'General Articles'),
            ('herramientas', 'Tools'),
        ],
        string="Material Type",
        help="Catalog of material type. Use it for goods (not services).",
    )