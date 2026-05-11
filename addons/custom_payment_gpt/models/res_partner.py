from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo para habilitar el comportamiento solicitado
    x_allow_partial_portal_payment = fields.Boolean(
        string="Permitir Abonos en Portal",
        help="Si está marcado, el cliente podrá ingresar montos parciales al pagar facturas desde el portal."
    )