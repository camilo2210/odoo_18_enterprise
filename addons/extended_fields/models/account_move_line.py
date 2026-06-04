# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    pgm_alternate_account = fields.Char(
        string="Alternate Account",
        related='account_id.pgm_alternate_account',   # cambia si tu cuenta usa otro técnico
        store=True,
        readonly=True,
        help="Concatenation defined in the accounting account (visible in entries/journal items).",
    )

    pgm_identification_type_id = fields.Many2one(
        "l10n_latam.identification.type",
        string="Identification type",
        readonly=True,
        store=True,
        compute="compute_pgm_identification_type_id"
    )

    pgm_identification_number = fields.Char(
        string="Identification Number",
        related='partner_id.vat',
        store=True,
        readonly=True,
        help="Identification number of the contact (VAT/NIT/RUT, etc.).",
    )

    pgm_linked_company_code = fields.Char(
        string="Linked Company Code",
        compute="_compute_pgm_partner_fields",
        store=True,
        readonly=False,
        help="Linked company code for intercompany operations.",
    )

    pgm_link_type = fields.Selection(
        selection=[
            ('matriz', 'Parent Company (Controlling)'),
            ('filial', 'Subsidiary (Controlled)'),
            ('subsidiaria', 'Indirect Subsidiary (Indirectly Controlled)'),
            ('asociada', 'Associate (Significant Influence)'),
            ('joint_venture', 'Joint Venture'),
            ('consorcio_ut', 'Consortium / Temporary Union'),
            ('empresa_vinculada', 'Related Company (Other)'),
        ],
        string="Link Type",
        compute="_compute_pgm_partner_fields",
        store=True,
        readonly=False,
        help="Corporate relationship with the company.",
    )

    pgm_trm = fields.Float(
        string="TRM",
        compute="_compute_pgm_trm",
        store=True,
        digits=(16, 6),
        help="Entry Rate (TRM): balance / foreign currency amount (amount_currency)."
    )
    
    pgm_intercompany_ref = fields.Char(
        string="Intercompany Ref",
        help="Intercompany reference associated with the journal item.",
    )

    pgm_detail = fields.Text(
        string="Detail",
        help="Field for additional details of the journal item.",
    )

    pgm_notes = fields.Text(
        string="Notes",
        help="Additional notes for the journal item.",
    )

    l10n_latam_document_number = fields.Char(
        string="Document Number",
        related='move_id.l10n_latam_document_number',
        store=True,
        readonly=True,
        help="Document number from the related journal entry.",
    )

    @api.depends('balance', 'amount_currency', 'currency_id')
    def _compute_pgm_trm(self):
        for line in self:
            # Solo aplica cuando hay moneda extranjera y monto distinto de cero
            if line.currency_id and line.amount_currency:
                line.pgm_trm = (line.balance or 0.0) / line.amount_currency
            else:
                line.pgm_trm = 0.0


    @api.depends("partner_id")
    def compute_pgm_identification_type_id(self):
        for record in self:
            if record.partner_id and hasattr(record.partner_id, 'l10n_latam_identification_type_id'):
                record.pgm_identification_type_id = record.partner_id.l10n_latam_identification_type_id
            else:
                record.pgm_identification_type_id = False
                

    @api.depends('partner_id.pgm_linked_company', 'partner_id.pgm_link_type', 'partner_id')
    def _compute_pgm_partner_fields(self):
        """
        Trae los valores de sociedad vinculada y tipo de vínculo desde el partner de la línea.
        """
        for line in self:
            if line.partner_id:
                line.pgm_linked_company_code = line.partner_id.pgm_linked_company or False
                line.pgm_link_type = line.partner_id.pgm_link_type or False
            else:
                line.pgm_linked_company_code = False
                line.pgm_link_type = False