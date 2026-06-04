# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class AccountAccount(models.Model):
    _inherit = 'account.account'

    pgm_alternate_code = fields.Char(
        string="Alternate Code",
        help="Free-form Text (No length limit).",
    )

    pgm_alternate_name = fields.Char(
        string="Alternate Name",
        help="Free-form Text (No length limit).",
    )

    pgm_alternate_account = fields.Char(
        string="Alternate Account",
        compute="_compute_pgm_alternate_account",
        store=True,
        help="Concatenation of Alternate Code and Alternate Name, separated by a space.",
    )

    pgm_account_description = fields.Char(
        string="Account Description",
        store=True,
        help="Extended description of the account.",
    )

    @api.depends('pgm_alternate_code', 'pgm_alternate_name')
    def _compute_pgm_alternate_account(self):
        for rec in self:
            code = (rec.pgm_alternate_code or '').strip()
            name = (rec.pgm_alternate_name or '').strip()
            rec.pgm_alternate_account = (f"{code} {name}").strip() or False

    # @api.constrains('pgm_alternate_code')
    # def _check_pgm_alternate_code_numeric(self):
    #     for rec in self:
    #         if rec.pgm_alternate_code and not re.fullmatch(r'\d+', rec.pgm_alternate_code.strip()):
    #             raise ValidationError(_("El 'Código alterno' debe contener solo dígitos."))

    # @api.constrains('pgm_alternate_name')
    # def _check_pgm_alternate_name_alpha(self):
    #     for rec in self:
    #         if rec.pgm_alternate_name and not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-\.'+]+", rec.pgm_alternate_name.strip()):
    #             raise ValidationError(_("El 'Nombre alterno' debe contener solo letras y separadores."))
