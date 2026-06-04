# -*- coding: utf-8 -*-
from odoo import fields, models


class SociedadVinculada(models.Model):
    _name = 'sociedad.vinculada'
    _description = 'Sociedad Vinculada'

    # Títulos (solo lectura, para usarlos en vistas)
    pgm_contacts_register_title = fields.Char(
        string="CONTACTS REGISTRY",
        default="CONTACTS REGISTRY",
        readonly=True,
        help="Visual title for the 'CONTACTS REGISTRY' section.",
        oldname='registro_de_contactos_titulo',
    )

    pgm_asset_location_title = fields.Char(
        string="ASSET LOCATION",
        default="ASSET LOCATION",
        readonly=True,
        help="Visual title for the 'ASSET LOCATION' section.",
        oldname='ubicacion_activo_titulo',
    )
