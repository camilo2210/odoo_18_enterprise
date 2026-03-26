# -*- coding: utf-8 -*-
import os
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SFTPBankConfig(models.Model):
    _name = 'sftp.bank.config'
    _description = 'SFTP Bank Statement Import Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ── Identification ────────────────────────────────────────────────────
    name = fields.Char(
        string='Configuration Name',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )

    # ── SFTP Connection ───────────────────────────────────────────────────
    sftp_host = fields.Char(
        string='SFTP Host',
        required=True,
        help='Hostname or IP address of the SFTP server',
    )
    sftp_port = fields.Integer(
        string='Port',
        default=22,
        required=True,
    )
    sftp_user = fields.Char(
        string='Username',
        required=True,
    )
    auth_method = fields.Selection(
        selection=[
            ('password', 'Password'),
            ('key', 'Private Key (PEM)'),
        ],
        string='Authentication Method',
        default='password',
        required=True,
    )
    sftp_password = fields.Char(
        string='Password',
        password=True,  # Odoo masks the field in UI
        groups='base.group_system',
    )
    sftp_private_key = fields.Text(
        string='Private Key Content (PEM)',
        help='Paste the full content of the private key (RSA, Ed25519, ECDSA)',
        groups='base.group_system',
    )
    sftp_key_passphrase = fields.Char(
        string='Key Passphrase',
        password=True,
        groups='base.group_system',
        help='Passphrase for the private key, if protected',
    )

    # ── Remote Paths ─────────────────────────────────────────────────────
    source_path = fields.Char(
        string='Source Path',
        required=True,
        default='/incoming',
        help='Remote directory to scan for CSV files',
    )
    processed_path = fields.Char(
        string='Processed Path',
        required=True,
        default='/processed',
        help='Remote directory where processed files will be moved',
    )
    file_keywords = fields.Char(
        string='File Keywords (comma-separated)',
        help='Filter files whose name contains at least one keyword. '
             'Leave empty to process all CSV files.',
    )

    # ── Accounting ────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Bank Journal',
        required=True,
        domain=[('type', 'in', ['bank', 'cash'])],
        tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='journal_id.company_id',
        store=True,
        readonly=True,
    )

    # ── CSV Settings ──────────────────────────────────────────────────────
    csv_separator = fields.Char(
        string='Column Separator',
        default=',',
        required=True,
        help='Single character used as CSV column delimiter',
    )
    csv_encoding = fields.Char(
        string='File Encoding',
        default='utf-8',
        required=True,
        help='E.g.: utf-8, latin-1, cp1252',
    )
    csv_has_header = fields.Boolean(
        string='First Row Is Header',
        default=True,
    )
    decimal_separator = fields.Selection(
        selection=[
            ('.', 'Dot (1,234.56)'),
            (',', 'Comma (1.234,56)'),
        ],
        string='Decimal Separator',
        default='.',
        required=True,
    )

    # ── Column Mapping ────────────────────────────────────────────────────
    col_date = fields.Char(
        string='Date Column Name',
        required=True,
        default='date',
        help='Exact header name of the date column in the CSV',
    )
    col_reference = fields.Char(
        string='Reference/Label Column Name',
        required=True,
        default='reference',
        help='Exact header name of the description/reference column',
    )
    col_amount = fields.Char(
        string='Amount Column Name',
        required=True,
        default='amount',
        help='Exact header name of the transaction amount column',
    )
    col_partner = fields.Char(
        string='Partner Column Name (optional)',
        help='Exact header name of the partner/counterpart column',
    )
    date_format = fields.Char(
        string='Date Format',
        default='%d/%m/%Y',
        required=True,
        help='Python strptime format: e.g. %d/%m/%Y or %Y-%m-%d',
    )

    # ── Relations ─────────────────────────────────────────────────────────
    log_ids = fields.One2many(
        comodel_name='sftp.import.log',
        inverse_name='config_id',
        string='Import Logs',
        readonly=True,
    )
    log_count = fields.Integer(
        string='Logs',
        compute='_compute_log_count',
    )

    # ── Computed ──────────────────────────────────────────────────────────
    @api.depends('log_ids')
    def _compute_log_count(self):
        for record in self:
            record.log_count = len(record.log_ids)

    # ── Constraints ───────────────────────────────────────────────────────
    @api.constrains('auth_method', 'sftp_password', 'sftp_private_key')
    def _check_credentials(self):
        for rec in self:
            if rec.auth_method == 'password' and not rec.sftp_password:
                raise ValidationError(
                    _('A password is required when using Password authentication.')
                )
            if rec.auth_method == 'key' and not rec.sftp_private_key:
                raise ValidationError(
                    _('A private key is required when using Private Key authentication.')
                )

    @api.constrains('csv_separator')
    def _check_separator(self):
        for rec in self:
            if not rec.csv_separator or len(rec.csv_separator) != 1:
                raise ValidationError(
                    _('CSV Separator must be exactly one character (e.g. "," or ";").')
                )

    # ── UI Actions ────────────────────────────────────────────────────────
    def action_test_connection(self):
        """Test SFTP connectivity and return a user notification."""
        self.ensure_one()
        # Import here to avoid circular imports at module load time
        from ..services.sftp_service import SFTPService
        try:
            sftp = SFTPService(self)
            sftp.connect()
            files = sftp.list_files(self.source_path)
            sftp.close()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Connected to %s:%s — %d file(s) found in %s') % (
                        self.sftp_host, self.sftp_port, len(files), self.source_path,
                    ),
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as exc:
            raise UserError(_('Connection failed: %s') % str(exc)) from exc

    def action_run_import(self):
        """Manual import trigger from the form view button."""
        self.ensure_one()
        self._run_import()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Complete'),
                'message': _('Process finished. Check the import logs for details.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_logs(self):
        """Open smart button logs view."""
        self.ensure_one()
        return {
            'name': _('Import Logs — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'sftp.import.log',
            'view_mode': 'list,form',
            'domain': [('config_id', '=', self.id)],
            'context': {'default_config_id': self.id},
        }

    # ── Cron Entry Point ─────────────────────────────────────────────────
    @api.model
    def run_all_imports(self):
        """
        Called by ir.cron. Iterates all active configurations and runs each import.
        Individual failures are logged but do NOT halt the overall process.
        """
        configs = self.search([('active', '=', True)])
        _logger.info('SFTP Importer: Starting scheduled run — %d active config(s).', len(configs))
        for config in configs:
            try:
                config._run_import()
            except Exception as exc:
                _logger.exception(
                    'SFTP Importer: Unhandled error in config "%s": %s',
                    config.name,
                    exc,
                )
        _logger.info('SFTP Importer: Scheduled run finished.')

    # ── Core Import Logic ─────────────────────────────────────────────────
    def _run_import(self):
        """
        Main orchestrator for a single configuration.
        1. Connect to SFTP
        2. List and filter CSV files
        3. Skip already-processed files
        4. Process each file (parse → create statement → archive)
        """
        self.ensure_one()
        from ..services.sftp_service import SFTPService

        _logger.info('SFTP Importer [%s]: Starting import run.', self.name)

        # Step 1: Connect
        sftp = SFTPService(self)
        try:
            sftp.connect()
        except Exception as exc:
            msg = _('SFTP connection failed: %s') % str(exc)
            _logger.error('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename='N/A', state='error', message=msg)
            return

        try:
            # Step 2: List and filter files
            all_files = sftp.list_files(self.source_path)
            csv_files = [f for f in all_files if f.lower().endswith('.csv')]
            filtered = self._filter_by_keywords(csv_files)

            _logger.info(
                'SFTP Importer [%s]: %d total files → %d CSV → %d after keyword filter.',
                self.name, len(all_files), len(csv_files), len(filtered),
            )

            # Step 3 & 4: Process each candidate file
            for filename in filtered:
                if self._is_already_processed(filename):
                    _logger.info(
                        'SFTP Importer [%s]: Skipping "%s" (already imported).',
                        self.name, filename,
                    )
                    continue
                self._process_single_file(sftp, filename)

        except Exception as exc:
            _logger.exception(
                'SFTP Importer [%s]: Error during file listing/processing: %s',
                self.name, exc,
            )
        finally:
            sftp.close()

        _logger.info('SFTP Importer [%s]: Import run completed.', self.name)

    def _filter_by_keywords(self, filenames):
        """
        Filter filenames using OR logic on configured keywords (case-insensitive).
        Returns all files when no keywords are configured.
        """
        if not self.file_keywords:
            return filenames
        keywords = [kw.strip().lower() for kw in self.file_keywords.split(',') if kw.strip()]
        return [f for f in filenames if any(kw in f.lower() for kw in keywords)] if keywords else filenames

    def _is_already_processed(self, filename):
        """Return True if this filename was already successfully imported for this config."""
        return bool(
            self.env['sftp.import.log'].search_count([
                ('config_id', '=', self.id),
                ('filename', '=', filename),
                ('state', '=', 'success'),
            ])
        )

    def _process_single_file(self, sftp, filename):
        """
        Full lifecycle for one CSV file:
        download → validate → parse → create statement → archive → log.
        Any step can fail independently; errors are logged without stopping other files.
        """
        from ..services.csv_parser import CSVParser

        _logger.info('SFTP Importer [%s]: Processing "%s".', self.name, filename)
        remote_src = '/'.join([self.source_path.rstrip('/'), filename])

        # ── Download ──────────────────────────────────────────────────────
        try:
            raw_bytes = sftp.read_file(remote_src)
        except Exception as exc:
            msg = _('Cannot read "%s": %s') % (filename, exc)
            _logger.error('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename=filename, state='error', message=msg)
            return

        # ── Validate not empty ────────────────────────────────────────────
        if not raw_bytes or not raw_bytes.strip():
            msg = _('File "%s" is empty, skipping.') % filename
            _logger.warning('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename=filename, state='skipped', message=msg)
            return

        # ── Parse CSV ─────────────────────────────────────────────────────
        try:
            parser = CSVParser(self)
            rows = parser.parse(raw_bytes)
        except Exception as exc:
            msg = _('CSV parse error in "%s": %s') % (filename, exc)
            _logger.error('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename=filename, state='error', message=msg)
            return

        if not rows:
            msg = _('File "%s" produced no valid rows after parsing.') % filename
            _logger.warning('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename=filename, state='skipped', message=msg)
            return

        # ── Create Bank Statement ─────────────────────────────────────────
        try:
            statement = self._create_bank_statement(filename, rows)
        except Exception as exc:
            msg = _('Error creating bank statement from "%s": %s') % (filename, exc)
            _logger.error('SFTP Importer [%s]: %s', self.name, msg)
            self._write_log(filename=filename, state='error', message=msg)
            return

        # ── Archive File ──────────────────────────────────────────────────
        try:
            remote_dst = '/'.join([self.processed_path.rstrip('/'), filename])
            sftp.move_file(remote_src, remote_dst)
            _logger.info(
                'SFTP Importer [%s]: Archived "%s" → "%s".',
                self.name, remote_src, remote_dst,
            )
        except Exception as exc:
            # Non-fatal: log warning but don't fail the import
            _logger.warning(
                'SFTP Importer [%s]: Could not archive "%s": %s. '
                'Statement was created but file was not moved.',
                self.name, filename, exc,
            )

        # ── Success Log ───────────────────────────────────────────────────
        self._write_log(
            filename=filename,
            state='success',
            message=_('Imported %d line(s) successfully.') % len(rows),
            statement_id=statement.id,
            lines_count=len(rows),
        )
        _logger.info(
            'SFTP Importer [%s]: "%s" done — %d lines imported.',
            self.name, filename, len(rows),
        )

    def _create_bank_statement(self, filename, rows):
        """
        Create account.bank.statement + account.bank.statement.line records.
        Compatible with Odoo v16/17/18 (detects available fields dynamically).
        """
        today = fields.Date.today()
        stmt_name = os.path.splitext(filename)[0]

        # Build statement vals — detect balance fields for backward compat
        BankStatement = self.env['account.bank.statement']
        stmt_vals = {
            'name': stmt_name,
            'date': today,
            'journal_id': self.journal_id.id,
        }
        if 'balance_start' in BankStatement._fields:
            stmt_vals['balance_start'] = 0.0
        if 'balance_end_real' in BankStatement._fields:
            stmt_vals['balance_end_real'] = 0.0

        statement = BankStatement.create(stmt_vals)

        # Determine reference field name (v16+: payment_ref / v15-: name)
        BankStatementLine = self.env['account.bank.statement.line']
        ref_field = 'payment_ref' if 'payment_ref' in BankStatementLine._fields else 'name'

        # Build lines batch
        line_vals_list = []
        for row in rows:
            vals = self._prepare_line_vals(statement, row, ref_field)
            if vals:
                line_vals_list.append(vals)

        if not line_vals_list:
            statement.unlink()
            raise UserError(
                _('No valid statement lines could be prepared from "%s".') % filename
            )

        BankStatementLine.create(line_vals_list)
        return statement

    def _prepare_line_vals(self, statement, row, ref_field):
        """
        Map a parsed CSV row dict to account.bank.statement.line create values.
        Returns None to skip a row silently.
        """
        try:
            date_val = row.get('date')
            reference = row.get('reference') or ''
            amount = row.get('amount')
            partner_name = (row.get('partner') or '').strip()

            if not date_val or amount is None:
                return None

            vals = {
                'statement_id': statement.id,
                'journal_id': self.journal_id.id,
                'date': date_val,
                ref_field: reference,
                'amount': amount,
            }

            # Attempt partner resolution
            if partner_name:
                partner = self.env['res.partner'].search(
                    [('name', 'ilike', partner_name)], limit=1
                )
                if partner:
                    vals['partner_id'] = partner.id
                # partner_name field exists in older Odoo versions
                elif 'partner_name' in self.env['account.bank.statement.line']._fields:
                    vals['partner_name'] = partner_name

            return vals

        except Exception as exc:
            _logger.warning('Skipping invalid row %s: %s', row, exc)
            return None

    # ── Helpers ───────────────────────────────────────────────────────────
    def _write_log(self, filename, state, message, statement_id=None, lines_count=0):
        """Create an sftp.import.log record for audit trail."""
        self.env['sftp.import.log'].create({
            'config_id': self.id,
            'filename': filename,
            'state': state,
            'message': message,
            'statement_id': statement_id,
            'lines_imported': lines_count,
        })