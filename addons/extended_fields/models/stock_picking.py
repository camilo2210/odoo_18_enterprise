# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        """
        Regla: No permitir validar si alguna move en move_ids_without_package
        tiene quantity_done > product_uom_qty.
        """
        for picking in self:
            overflow = []
            for move in picking.move_ids_without_package:
                qty_done = getattr(move, "quantity", 0.0)
                qty_demand = getattr(move, "product_uom_qty", 0.0)
                if qty_done > qty_demand:
                    name = move.product_id.display_name or move.product_id.name or move.name or _("Línea")
                    overflow.append(
                        f"- {name}: hecho={qty_done:g} > pedido={qty_demand:g} {move.product_uom.name or ''}"
                    )

            if overflow:
                details = "\n".join(overflow)
                raise ValidationError(
                    _(
                        "No puedes validar este albarán porque existen líneas con cantidad hecha "
                        "mayor a la solicitada:\n%s\n\nAjusta las cantidades antes de validar."
                    ) % details
                )

        # Si todo OK, continúa el flujo estándar
        return super().button_validate()
