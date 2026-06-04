# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    # pgm_fiscal_registry = fields.Char(
    #     string="Fiscal Log",
    #     help="Fiscal Log associated with the document.",
    # )

    # pgm_consecutive_number = fields.Char(
    #     string="consecutive",
    #     help="Internal/DIAN consecutive number of the document.",
    # )

    l10n_latam_identification_type_id = fields.Many2one(
        'l10n_latam.identification.type',
        string="Identification (type)",
        related='partner_id.l10n_latam_identification_type_id',
        store=True,
        readonly=True,
    )

    pgm_identification_number = fields.Char(
        string="Identification",
        related='partner_id.vat',
        store=True,
        readonly=True,
        help="Customer/Vendor Identification Number (VAT/NIT/RUT, etc.)",
        oldname='identificacion',
    )

    pgm_payroll_document_type = fields.Selection(
        selection=[
            ('nominai', 'Individual Payroll'),
            ('nominai_ad', 'Individual Payroll Adjustment'),
            ('nominag', 'Group Payroll'),
            ('nominag_ad', 'Group Payroll Adjustment'),
        ],
        string="Payroll Document Type",
        help="Payroll document type for electronic DIAN reports.",
        oldname='tipo_documento_nomina',
    )


    pgm_payment_proposal = fields.Char(
        string="Payment proposal",
        help="Notes or reference for payment proposals.",
    )

    @api.model
    def _get_related_purchase_orders(self, moves):
        """Obtiene los purchase.order vinculados a las líneas de la factura."""
        PurchaseOrder = self.env['purchase.order']
        po_ids = PurchaseOrder.browse()
        for move in moves if getattr(moves, 'ids', False) else self.browse([moves.id]):
            pols = move.invoice_line_ids.mapped('purchase_line_id').filtered(lambda l: l.order_id)
            po_ids |= pols.mapped('order_id')
        return po_ids

    # def action_post(self):
    #     """Al postear: si la factura proviene de OC, heredar Registro DIAN y Consecutivo."""
    #     res = super().action_post()
    #     for move in self:
    #         if move.move_type in ('in_invoice', 'in_refund'):
    #             pos = self._get_related_purchase_orders(move)
    #             if pos:
    #                 po = pos[0]
    #                 if not move.pgm_fiscal_registry and hasattr(po, 'pgm_fiscal_registry'):
    #                     move.pgm_fiscal_registry = po.pgm_fiscal_registry
    #                 if not move.pgm_consecutive_number and hasattr(po, 'pgm_consecutive_number'):
    #                     move.pgm_consecutive_number = po.pgm_consecutive_number
    #     return res
