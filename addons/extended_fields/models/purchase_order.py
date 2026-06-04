# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.misc import formatLang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # pgm_fiscal_registry = fields.Char(
            # string="Fiscal log",
            # help="Fiscal log associated with the purchase order.",
        # )

    # pgm_consecutive_number = fields.Char(
        # string="Sequence",
        # help="Internal/DIAN consecutive number of the purchase order.",
    # )
    pgm_vendor_delivery_address = fields.Char(
        string="Delivery Address",
        help="Automatically filled with the vendor's first delivery address when selected."
    )

    @staticmethod
    def _build_address_line(p):
        """Devuelve una línea de dirección compacta y legible (sin saltos de línea)."""
        parts = [
            p.street or '',
            p.street2 or '',
            (p.city or ''),
            (p.state_id and p.state_id.name) or '',
            (p.zip or ''),
            (p.country_id and p.country_id.name) or '',
        ]
        # Limpia espacios extra y separa con coma
        parts = [x.strip() for x in parts if x and x.strip()]
        return ', '.join(parts)

    @api.onchange('partner_id')
    def _onchange_partner_id_fill_delivery_char(self):
        """Al cambiar el proveedor, poner en pgm_vendor_delivery_address la primera dirección de entrega."""
        for order in self:
            order.pgm_vendor_delivery_address = False
            partner = order.partner_id
            if not partner:
                continue

            # 1) Usar lógica nativa para encontrar 'delivery'
            delivery_id = partner.address_get(adr_pref=['delivery']).get('delivery')
            if delivery_id:
                delivery = self.env['res.partner'].browse(delivery_id)
            else:
                # 2) Primer hijo con type='delivery' del comercial
                commercial = partner.commercial_partner_id
                delivery = (commercial.child_ids.filtered(lambda r: r.type == 'delivery')[:1]) or self.env['res.partner']
                delivery = delivery and delivery[0] or False

            # 3) Fallback: si no hay delivery explícito, usar el propio partner
            if not delivery:
                delivery = partner

            order.pgm_vendor_delivery_address = self._build_address_line(delivery)

    @api.depends('name', 'amount_total', 'currency_id')
    @api.depends_context('display_po_amount')
    def _compute_display_name(self):
        if not self.env.context.get('display_po_amount'):
            return super(PurchaseOrder, self)._compute_display_name()

        for po in self:
            amount_str = formatLang(self.env, po.amount_total or 0.0, currency_obj=po.currency_id) \
                         if po.currency_id else str(po.amount_total or 0.0)
            base = po.name or ''
            po.display_name = f"{base} - {amount_str}"