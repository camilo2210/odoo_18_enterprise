# -*- coding: utf-8 -*-
import logging
import json
import requests
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class ShopifyPayout(models.Model):
    _name = 'shopify.payout'
    _description = 'Shopify Payout Report'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Payout Reference', required=True, tracking=True)
    instance_id = fields.Many2one('shopify.instance', string='Shopify Instance', required=True, ondelete='cascade')
    
    # Payout Details
    payout_reference_id = fields.Char('Shopify Payout ID', required=True, tracking=True)
    payout_date = fields.Date('Payout Date', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, tracking=True)
    amount = fields.Monetary('Total Amount', currency_field='currency_id', tracking=True)
    fee_amount = fields.Monetary('Fee Amount', currency_field='currency_id', tracking=True)
    net_amount = fields.Monetary('Net Amount', currency_field='currency_id', tracking=True)
    
    # Status
    payout_status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_transit', 'In Transit'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Payout Status', default='scheduled', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('partially_reconciled', 'Partially Reconciled'),
        ('reconciled', 'Reconciled'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Bank Statement Integration
    statement_id = fields.Many2one('account.bank.statement', string='Bank Statement', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, 
                                domain=[('type', '=', 'bank')], tracking=True)
    
    # Transaction Lines
    transaction_line_ids = fields.One2many('shopify.payout.transaction', 'payout_id', string='Transaction Lines')
    
    # Analytics
    transaction_count = fields.Integer('Transaction Count', compute='_compute_analytics')
    order_count = fields.Integer('Order Count', compute='_compute_analytics')
    refund_count = fields.Integer('Refund Count', compute='_compute_analytics')
    chargeback_count = fields.Integer('Chargeback Count', compute='_compute_analytics')
    
    # Reconciliation
    reconciled_amount = fields.Monetary('Reconciled Amount', currency_field='currency_id', compute='_compute_reconciliation')
    unreconciled_amount = fields.Monetary('Unreconciled Amount', currency_field='currency_id', compute='_compute_reconciliation')
    reconciliation_rate = fields.Float('Reconciliation Rate (%)', compute='_compute_reconciliation')
    
    # Advanced Features
    exchange_rate = fields.Float('Exchange Rate', default=1.0, help='Exchange rate for currency conversion')
    base_currency_amount = fields.Monetary('Base Currency Amount', currency_field='base_currency_id', compute='_compute_base_amount')
    base_currency_id = fields.Many2one('res.currency', string='Base Currency', 
                                      default=lambda self: self.env.company.currency_id)
    
    # Audit Trail
    import_date = fields.Datetime('Import Date', default=fields.Datetime.now, readonly=True)
    last_reconciliation_date = fields.Datetime('Last Reconciliation Date', readonly=True)
    reconciled_by = fields.Many2one('res.users', string='Reconciled By', readonly=True)
    
    # Configuration
    auto_reconcile = fields.Boolean('Auto Reconcile', default=True)
    create_bank_statement = fields.Boolean('Create Bank Statement', default=True)
    skip_import = fields.Boolean('Skip Import', default=False)
    
    note = fields.Text('Notes')
    
    _sql_constraints = [
        ('unique_payout_reference', 'unique(payout_reference_id, instance_id)', 
         'A payout with this reference already exists for this instance!'),
    ]

    @api.depends('transaction_line_ids')
    def _compute_analytics(self):
        for record in self:
            transactions = record.transaction_line_ids
            record.transaction_count = len(transactions)
            record.order_count = len(transactions.filtered(lambda t: t.transaction_type == 'sale'))
            record.refund_count = len(transactions.filtered(lambda t: t.transaction_type == 'refund'))
            record.chargeback_count = len(transactions.filtered(lambda t: t.transaction_type == 'chargeback'))

    @api.depends('transaction_line_ids.reconciled', 'amount')
    def _compute_reconciliation(self):
        for record in self:
            reconciled_transactions = record.transaction_line_ids.filtered(lambda t: t.reconciled)
            record.reconciled_amount = sum(reconciled_transactions.mapped('amount'))
            record.unreconciled_amount = record.amount - record.reconciled_amount
            record.reconciliation_rate = (record.reconciled_amount / record.amount * 100) if record.amount else 0

    @api.depends('amount', 'exchange_rate', 'currency_id', 'base_currency_id')
    def _compute_base_amount(self):
        for record in self:
            if record.currency_id and record.base_currency_id:
                record.base_currency_amount = record.currency_id._convert(
                    record.amount, record.base_currency_id, 
                    record.env.company, record.payout_date or fields.Date.today()
                )
            else:
                record.base_currency_amount = record.amount

    def action_import_payout(self):
        """Import payout data from Shopify"""
        for record in self:
            try:
                record._import_payout_from_shopify()
                record.state = 'imported'
                record.message_post(body=_('Payout imported successfully from Shopify'))
            except Exception as e:
                record.message_post(body=_('Failed to import payout: %s') % str(e))
                raise UserError(_('Failed to import payout: %s') % str(e))

    def action_create_bank_statement(self):
        """Create bank statement for payout"""
        for record in self:
            try:
                record._create_bank_statement()
                record.message_post(body=_('Bank statement created successfully'))
            except Exception as e:
                record.message_post(body=_('Failed to create bank statement: %s') % str(e))
                raise UserError(_('Failed to create bank statement: %s') % str(e))

    def action_reconcile_transactions(self):
        """Reconcile payout transactions"""
        for record in self:
            try:
                record._reconcile_transactions()
                record.message_post(body=_('Transactions reconciled successfully'))
            except Exception as e:
                record.message_post(body=_('Failed to reconcile transactions: %s') % str(e))
                raise UserError(_('Failed to reconcile transactions: %s') % str(e))

    def action_validate_payout(self):
        """Validate payout and mark as completed"""
        for record in self:
            if record.state != 'reconciled':
                raise UserError(_('Payout must be reconciled before validation'))
            
            record.state = 'validated'
            record.message_post(body=_('Payout validated successfully'))

    def _import_payout_from_shopify(self):
        """Import payout data from Shopify API"""
        instance = self.instance_id
        
        # Connect to Shopify
        headers = {
            'X-Shopify-Access-Token': instance.access_token or instance.password,
            'Content-Type': 'application/json',
        }
        
        # Get payout details
        url = f"{instance.shop_url}/admin/api/2024-01/shopify_payments/payouts/{self.payout_reference_id}.json"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise UserError(_('Failed to fetch payout from Shopify. Status: %s') % response.status_code)
        
        payout_data = response.json().get('payout', {})
        
        # Update payout details
        self.write({
            'payout_date': payout_data.get('date'),
            'amount': float(payout_data.get('amount', 0)),
            'fee_amount': float(payout_data.get('fee', 0)),
            'net_amount': float(payout_data.get('net', 0)),
            'payout_status': payout_data.get('status', 'scheduled'),
            'currency_id': self._get_currency_id(payout_data.get('currency')),
        })
        
        # Import transactions
        self._import_payout_transactions()

    def _import_payout_transactions(self):
        """Import payout transactions from Shopify"""
        instance = self.instance_id
        
        headers = {
            'X-Shopify-Access-Token': instance.access_token or instance.password,
            'Content-Type': 'application/json',
        }
        
        # Get transactions for this payout
        url = f"{instance.shop_url}/admin/api/2024-01/shopify_payments/payouts/{self.payout_reference_id}/transactions.json"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise UserError(_('Failed to fetch transactions from Shopify. Status: %s') % response.status_code)
        
        transactions_data = response.json().get('transactions', [])
        
        # Create transaction records
        for transaction_data in transactions_data:
            self.env['shopify.payout.transaction'].create({
                'payout_id': self.id,
                'transaction_id': str(transaction_data.get('id')),
                'transaction_type': transaction_data.get('type'),
                'amount': float(transaction_data.get('amount', 0)),
                'fee': float(transaction_data.get('fee', 0)),
                'net_amount': float(transaction_data.get('net', 0)),
                'currency': transaction_data.get('currency'),
                'source_order_id': transaction_data.get('source_order_id'),
                'source_order_transaction_id': transaction_data.get('source_order_transaction_id'),
                'processed_at': transaction_data.get('processed_at'),
                'test': transaction_data.get('test', False),
            })

    def _create_bank_statement(self):
        """Create bank statement for payout"""
        if not self.journal_id:
            raise UserError(_('Journal is required to create bank statement'))
        
        # Create bank statement
        statement_vals = {
            'name': f"Shopify Payout {self.name}",
            'journal_id': self.journal_id.id,
            'date': self.payout_date,
            'balance_start': 0.0,
            'balance_end_real': self.net_amount,
            'shopify_payout_id': self.id,
        }
        
        statement = self.env['account.bank.statement'].create(statement_vals)
        
        # Create statement lines for transactions
        for transaction in self.transaction_line_ids:
            if transaction.transaction_type in ['sale', 'refund']:
                statement_line_vals = {
                    'statement_id': statement.id,
                    'date': transaction.processed_at or self.payout_date,
                    'name': f"{transaction.transaction_type.title()} - {transaction.source_order_id or transaction.transaction_id}",
                    'amount': transaction.net_amount,
                    'partner_id': self._get_partner_from_order(transaction.source_order_id),
                    'shopify_transaction_id': transaction.id,
                }
                self.env['account.bank.statement.line'].create(statement_line_vals)
        
        self.write({
            'statement_id': statement.id,
            'state': 'imported',
        })

    def _reconcile_transactions(self):
        """Reconcile payout transactions with Odoo records"""
        for transaction in self.transaction_line_ids:
            if transaction.transaction_type == 'sale' and transaction.source_order_id:
                # Find corresponding sale order
                sale_order = self.env['sale.order'].search([
                    ('shopify_order_id', '=', transaction.source_order_id),
                    ('shopify_instance_id', '=', self.instance_id.id)
                ], limit=1)
                
                if sale_order:
                    # Find corresponding invoice
                    invoice = sale_order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                    
                    if invoice:
                        # Reconcile with bank statement line
                        statement_line = self.env['account.bank.statement.line'].search([
                            ('shopify_transaction_id', '=', transaction.id)
                        ], limit=1)
                        
                        if statement_line:
                            # Create reconciliation
                            self.env['account.reconciliation.widget']._create_reconciliation(
                                statement_line, invoice
                            )
                            transaction.write({'reconciled': True})
        
        # Update reconciliation status
        if self.transaction_line_ids.filtered(lambda t: t.reconciled):
            self.write({
                'state': 'partially_reconciled' if self.unreconciled_amount > 0 else 'reconciled',
                'last_reconciliation_date': fields.Datetime.now(),
                'reconciled_by': self.env.user.id,
            })

    def _get_currency_id(self, currency_code):
        """Get currency ID from currency code"""
        currency = self.env['res.currency'].search([('name', '=', currency_code)], limit=1)
        if not currency:
            # Create currency if it doesn't exist
            currency = self.env['res.currency'].create({
                'name': currency_code,
                'symbol': currency_code,
            })
        return currency.id

    def _get_partner_from_order(self, order_id):
        """Get partner from Shopify order ID"""
        if order_id:
            sale_order = self.env['sale.order'].search([
                ('shopify_order_id', '=', order_id),
                ('shopify_instance_id', '=', self.instance_id.id)
            ], limit=1)
            return sale_order.partner_id.id if sale_order else False
        return False

    @api.model
    def import_payouts_from_shopify(self, instance, start_date=None, end_date=None):
        """Import payouts from Shopify for a date range"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        headers = {
            'X-Shopify-Access-Token': instance.access_token or instance.password,
            'Content-Type': 'application/json',
        }
        
        # Get payouts for date range
        url = f"{instance.shop_url}/admin/api/2024-01/shopify_payments/payouts.json"
        params = {
            'date_min': start_date,
            'date_max': end_date,
            'status': 'paid',
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            raise UserError(_('Failed to fetch payouts from Shopify. Status: %s') % response.status_code)
        
        payouts_data = response.json().get('payouts', [])
        
        imported_count = 0
        for payout_data in payouts_data:
            payout_id = str(payout_data.get('id'))
            
            # Check if payout already exists
            existing_payout = self.search([
                ('payout_reference_id', '=', payout_id),
                ('instance_id', '=', instance.id)
            ], limit=1)
            
            if not existing_payout:
                # Create new payout
                payout_vals = {
                    'name': f"Payout {payout_id}",
                    'instance_id': instance.id,
                    'payout_reference_id': payout_id,
                    'payout_date': payout_data.get('date'),
                    'amount': float(payout_data.get('amount', 0)),
                    'fee_amount': float(payout_data.get('fee', 0)),
                    'net_amount': float(payout_data.get('net', 0)),
                    'payout_status': payout_data.get('status', 'scheduled'),
                    'currency_id': self._get_currency_id(payout_data.get('currency')),
                    'journal_id': instance.journal_id.id if instance.journal_id else False,
                }
                
                payout = self.create(payout_vals)
                
                # Import transactions
                payout._import_payout_transactions()
                
                imported_count += 1
        
        return imported_count

    def get_payout_summary(self):
        """Get payout summary for reporting"""
        return {
            'total_payouts': len(self),
            'total_amount': sum(self.mapped('amount')),
            'total_fees': sum(self.mapped('fee_amount')),
            'total_net': sum(self.mapped('net_amount')),
            'reconciled_amount': sum(self.mapped('reconciled_amount')),
            'unreconciled_amount': sum(self.mapped('unreconciled_amount')),
            'avg_reconciliation_rate': sum(self.mapped('reconciliation_rate')) / len(self) if self else 0,
        }

    @api.model
    def create(self, vals):
        """Override create to set default values"""
        if not vals.get('journal_id'):
            instance = self.env['shopify.instance'].browse(vals.get('instance_id'))
            if instance.journal_id:
                vals['journal_id'] = instance.journal_id.id
        
        return super().create(vals)

    def unlink(self):
        """Override unlink to clean up related records"""
        for record in self:
            if record.statement_id:
                record.statement_id.unlink()
        return super().unlink()


class ShopifyPayoutTransaction(models.Model):
    _name = 'shopify.payout.transaction'
    _description = 'Shopify Payout Transaction'
    _order = 'id desc'

    payout_id = fields.Many2one('shopify.payout', string='Payout', required=True, ondelete='cascade')
    transaction_id = fields.Char('Transaction ID', required=True)
    transaction_type = fields.Selection([
        ('sale', 'Sale'),
        ('refund', 'Refund'),
        ('chargeback', 'Chargeback'),
        ('fee', 'Fee'),
        ('adjustment', 'Adjustment'),
    ], string='Transaction Type', required=True)
    
    amount = fields.Monetary('Amount', currency_field='currency_id')
    fee = fields.Monetary('Fee', currency_field='currency_id')
    net_amount = fields.Monetary('Net Amount', currency_field='currency_id')
    currency = fields.Char('Currency')
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 compute='_compute_currency_id', store=True)
    
    source_order_id = fields.Char('Source Order ID')
    source_order_transaction_id = fields.Char('Source Order Transaction ID')
    processed_at = fields.Datetime('Processed At')
    test = fields.Boolean('Test Transaction', default=False)
    
    # Reconciliation
    reconciled = fields.Boolean('Reconciled', default=False)
    reconciled_date = fields.Datetime('Reconciled Date', readonly=True)
    reconciled_by = fields.Many2one('res.users', string='Reconciled By', readonly=True)
    
    # Related Records
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_related_records')
    invoice_id = fields.Many2one('account.move', string='Invoice', compute='_compute_related_records')
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Line')
    
    note = fields.Text('Notes')

    @api.depends('currency')
    def _compute_currency_id(self):
        for record in self:
            if record.currency:
                currency = self.env['res.currency'].search([('name', '=', record.currency)], limit=1)
                record.currency_id = currency.id if currency else False
            else:
                record.currency_id = False

    @api.depends('source_order_id', 'payout_id.instance_id')
    def _compute_related_records(self):
        for record in self:
            if record.source_order_id:
                record.sale_order_id = self.env['sale.order'].search([
                    ('shopify_order_id', '=', record.source_order_id),
                    ('shopify_instance_id', '=', record.payout_id.instance_id.id)
                ], limit=1)
                
                if record.sale_order_id:
                    record.invoice_id = record.sale_order_id.invoice_ids.filtered(
                        lambda inv: inv.state == 'posted'
                    )[:1]
            else:
                record.sale_order_id = False
                record.invoice_id = False

    def action_reconcile(self):
        """Manually reconcile transaction"""
        for record in self:
            if record.invoice_id and record.statement_line_id:
                # Create reconciliation
                self.env['account.reconciliation.widget']._create_reconciliation(
                    record.statement_line_id, record.invoice_id
                )
                record.write({
                    'reconciled': True,
                    'reconciled_date': fields.Datetime.now(),
                    'reconciled_by': self.env.user.id,
                })
                
                # Update payout reconciliation status
                record.payout_id._compute_reconciliation() 