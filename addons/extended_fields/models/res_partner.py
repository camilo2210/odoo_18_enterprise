# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    pgm_company_country_code = fields.Char(related='company_id.country_id.code', string="Country Code", readonly=True)

    # --- Debida diligencia: banderas ---
    pgm_authorize_risk_queries = fields.Boolean(
        string="Authorize Credit Bureau Inquiry",
    )
    pgm_authorize_risk_reporting = fields.Boolean(
        string="Authorize Credit Bureau Reporting",
    )
    pgm_registry_assets_check = fields.Boolean(
        string="Check Registry Assets",
    )
    pgm_transit_vehicles_check = fields.Boolean(
        string="Check Transit Vehicles",
    )
    pgm_due_diligence = fields.Boolean(
        string="Due Diligence",
        help="Check when due diligence has been performed.",
    )

    # Fecha automática al marcar Due Diligence
    pgm_date_due_diligence = fields.Date(
        string="Date Due Diligence",
        readonly=True,
        help="Date when 'Due Diligence' was marked. It updates automatically.",
    )

    # (Título visual opcional; mejor usar <separator/> en la vista)
    pgm_due_diligence_title = fields.Char(
        string="DUE DILIGENCE",
        default="DUE DILIGENCE",
        readonly=True,
            help="Read-only field used as a visual title/header.",
        )

    # --- Clasificaciones proveedor/empresa ---
    pgm_supplier_type = fields.Selection(
        selection=[
            ('nacional', 'NATIONAL'),
            ('exterior', 'FOREING'),
            # ('recurrente', 'RECURRENT'), 
            # ('no_recurrente', 'NON-RECURRENT'),
            # ('siniestro', 'SINISTER'),
            # ('entidad_financiera', 'FINANCIAL ENTITY'),
            ('colaboradores', 'COLLABORATORS'),
        ],
        string="Vendor Type",
    )

    pgm_linked_company = fields.Char(
        string="Related Company",
        help="Related Company Code or Name.",
    )

    pgm_link_type = fields.Selection(
        selection=[
            ('matriz', 'Parent Company (Controlling)'),
            ('filial', 'Subsidiary (Controlled)'),
            ('subsidiaria', 'Subsidiary (Indirectly Controlled)'),
            ('asociada', 'Associated (Significant Influence)'),
            ('joint_venture', 'Joint Venture'),
            ('consorcio_ut', 'Consortium / Temporary Union'),
            ('empresa_vinculada', 'Related Company (Others)'),
        ],
        string="Link Type",
        help="Related Company Relationship.",
    )

    # Cuenta analítica asociada al partner
    pgm_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account",
    )

    @api.onchange('pgm_due_diligence')
    def _onchange_pgm_due_diligence(self):
        for rec in self:
            if rec.pgm_due_diligence:
                rec.pgm_date_due_diligence = fields.Date.context_today(rec)
            else:
                rec.pgm_date_due_diligence = False

    def write(self, vals):
        res = super().write(vals)

        if 'pgm_due_diligence' in vals:
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.pgm_due_diligence:
                    rec.with_context(skip_invalidations=True).write({
                        'pgm_date_due_diligence': today
                    })
                else:
                    rec.with_context(skip_invalidations=True).write({
                        'pgm_date_due_diligence': False
                    })
        return res
