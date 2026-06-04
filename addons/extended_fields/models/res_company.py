# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Campo para almacenar la imagen de la firma
    firma_imagen = fields.Image(string="Imagen de Firma", help="Suba la imagen de la firma de la empresa")
    # Campo para almacenar la imagen del sello
    pgm_sello = fields.Image(string="Imagen de Sello", help="Suba la imagen del sello de la empresa")
    pgm_tyc_purchase=fields.Html(string="Términos y Condiciones de Compra", help="Ingrese los términos y condiciones para las compras en formato HTML")
    pgm_tyc_sale=fields.Html(string="Términos y Condiciones de Venta", help="Ingrese los términos y condiciones para las ventas en formato HTML")
    # Campo para almacenar nombre del firmante
    pgm_signed_by = fields.Char(string="Nombre del Firmante", help="Ingrese el nombre de la persona que firma en representación de la empresa")