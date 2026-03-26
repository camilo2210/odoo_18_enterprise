# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class SFTPImportLog(models.Model):
    _name = 'sftp.import.log'
    _description = 'SFTP Bank Statement Import Log'
    _order = 'create_date desc'
    _rec_name = 'filename'

    config_id = fields.Many2one(
        comodel_name='sftp.bank.config',
        string='Configuration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    filename = fields.Char(
        string='File Name',
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('error', 'Error'),
            ('skipped', 'Skipped'),
        ],
        string='Status',
        required=True,
        readonly=True,
    )
    message = fields.Text(
        string='Message / Detail',
        readonly=True,
    )
    statement_id = fields.Many2one(
        comodel_name='account.bank.statement',
        string='Bank Statement Created',
        readonly=True,
        ondelete='set null',
    )
    lines_imported = fields.Integer(
        string='Lines Imported',
        readonly=True,
        default=0,
    )
    import_date = fields.Datetime(
        string='Import Date',
        related='create_date',
        store=True,
        readonly=True,
    )

    # Convenience color coding for list view
    color = fields.Integer(
        string='Color',
        compute='_compute_color',
    )

    def _compute_color(self):
        color_map = {'success': 10, 'error': 1, 'skipped': 3}
        for rec in self:
            rec.color = color_map.get(rec.state, 0)

