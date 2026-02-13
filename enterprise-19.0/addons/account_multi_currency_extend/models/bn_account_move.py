# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class BnAccountMove(models.Model):
    _inherit = 'account.move'
    
    enable_second_currency_for_company = fields.Boolean(
        related='company_id.enable_second_currency_for_company', 
        store=True
    )
    company_second_currency_id = fields.Many2one(
        related='company_id.second_currency_id', 
        string='Company Second Currency', 
        readonly=True
    )


class BnAccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    exchange_amount = fields.Monetary(
        string='Exchange Amount',
        currency_field='exchange_currency',
        compute='_compute_exchange_amount',
        store=True,
        readonly=False,
        precompute=True
    )
    debit_exchange = fields.Monetary(
        string='Debit Exchange',
        currency_field='exchange_currency',
        compute='_compute_debit_credit_exchange',
        inverse='_inverse_debit_exchange',
        store=True,
        readonly=False,
        precompute=True
    )
    credit_exchange = fields.Monetary(
        string='Credit Exchange',
        currency_field='exchange_currency',
        compute='_compute_debit_credit_exchange',
        inverse='_inverse_credit_exchange',
        store=True,
        readonly=False,
        precompute=True
    )
    
    exchange_currency = fields.Many2one(
        'res.currency',
        related='company_id.second_currency_id',
        string="Company Second Currency",
        readonly=True,
        store=True
    )

    @api.depends('debit', 'credit', 'currency_id', 'amount_currency', 'company_id.second_currency_id', 'company_id.currency_id')
    def _compute_exchange_amount(self):
        """Compute exchange_amount (the balance in second currency)"""
        for rec in self:
            rec.exchange_amount = 0

            second_currency = rec.company_id.second_currency_id
            if not second_currency:
                continue

            company_currency = rec.company_id.currency_id
            conversion_date = rec.date or fields.Date.context_today(rec)

            # If line currency is already in second currency, use amount_currency
            if rec.currency_id == second_currency:
                rec.exchange_amount = rec.amount_currency
            else:
                # Convert balance (debit - credit) from company currency to second currency
                balance = rec.debit - rec.credit
                rec.exchange_amount = company_currency._convert(
                    balance,
                    second_currency,
                    rec.company_id,
                    conversion_date
                )

    @api.depends('exchange_amount')
    def _compute_debit_credit_exchange(self):
        """Compute debit_exchange and credit_exchange from exchange_amount"""
        for rec in self:
            if rec.exchange_amount > 0:
                rec.debit_exchange = rec.exchange_amount
                rec.credit_exchange = 0
            elif rec.exchange_amount < 0:
                rec.debit_exchange = 0
                rec.credit_exchange = abs(rec.exchange_amount)
            else:
                rec.debit_exchange = 0
                rec.credit_exchange = 0

    @api.onchange('debit_exchange')
    def _inverse_debit_exchange(self):
        """When debit_exchange is set, clear credit_exchange and update exchange_amount"""
        for rec in self:
            if rec.debit_exchange:
                rec.credit_exchange = 0
            rec.exchange_amount = rec.debit_exchange - rec.credit_exchange

    @api.onchange('credit_exchange')
    def _inverse_credit_exchange(self):
        """When credit_exchange is set, clear debit_exchange and update exchange_amount"""
        for rec in self:
            if rec.credit_exchange:
                rec.debit_exchange = 0
            rec.exchange_amount = rec.debit_exchange - rec.credit_exchange


class BnAccountTax(models.Model):
    _inherit = "account.tax"
    
    @api.constrains('tax_group_id')
    def validate_tax_group_id(self):
        for record in self:
            if (record.tax_group_id.country_id and 
                record.country_id and 
                record.tax_group_id.country_id != record.country_id):
                raise ValidationError(_(
                    "The tax group %s must have the same country_id %s "
                    "as the tax using it %s %s."
                ) % (
                    record.tax_group_id.name,
                    record.tax_group_id.country_id.name,
                    record.name,
                    record.country_id.name
                ))