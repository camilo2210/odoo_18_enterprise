# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from collections import defaultdict


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_ae_basic_salary = fields.Monetary(string="Basic Salary", compute="_compute_l10n_ae_basic_salary", currency_field="currency_id")
    l10n_ae_hourly_wage = fields.Monetary(string="Hourly Wage", compute="_compute_l10n_ae_hourly_wage", currency_field="currency_id")
    l10n_ae_hours_worked = fields.Float(string="Hours Worked", compute="_compute_l10n_ae_worked_values")
    l10n_ae_total_paid_hours = fields.Float(string="Total Paid Hours", compute="_compute_l10n_ae_worked_values")

    @api.depends(
        'worked_days_line_ids.number_of_hours',
        'worked_days_line_ids.code',
        'worked_days_line_ids.is_paid',
    )
    def _compute_l10n_ae_worked_values(self):
        all_lines = self.env['hr.payslip.worked_days']._read_group(
            domain=[('payslip_id', 'in', self.ids)],
            groupby=['payslip_id', 'code', 'is_paid'],
            aggregates=['number_of_hours:sum'],
        )
        values_by_payslip = defaultdict(lambda: {'l10n_ae_hours_worked': 0, 'l10n_ae_total_paid_hours': 0})
        for line in all_lines:
            # line = (hr.payslip(), code, is_paid, number_of_hours)
            payslip_id = line[0]

            if line[1] == 'WORK100':
                values_by_payslip[payslip_id.id]['l10n_ae_hours_worked'] += line[3]

            if line[2]:
                values_by_payslip[payslip_id.id]['l10n_ae_total_paid_hours'] += line[3]

        for record in self:
            record.update(values_by_payslip[record.id])

    @api.depends(
        'contract_id.wage_type',
        'contract_id.resource_calendar_id.hours_per_day',
        'contract_id.l10n_ae_housing_allowance',
        'contract_id.l10n_ae_transportation_allowance',
        'contract_id.l10n_ae_other_allowances'
    )
    def _compute_l10n_ae_hourly_wage(self):
        for record in self:
            if record.contract_id.wage_type == 'hourly':
                record.l10n_ae_hourly_wage = record.contract_id.hourly_wage
            else:
                hours = sum(self.worked_days_line_ids.mapped('number_of_days')) * record.contract_id.resource_calendar_id.hours_per_day
                gross = record.contract_id.wage + record.contract_id.l10n_ae_housing_allowance + record.contract_id.l10n_ae_transportation_allowance + record.contract_id.l10n_ae_other_allowances
                record.l10n_ae_hourly_wage = gross / hours if hours > 0 else 0

    def _get_l10n_ae_hourly_allowance_value(self, allowance_type):
        self.ensure_one()
        if allowance_type not in ('housing', 'transportation', 'other') or self.sum_worked_hours <= 0:
            return 0
        field = f'l10n_ae_{allowance_type}_allowance{"s" if allowance_type == "other" else ""}'
        return self.contract_id[field] / self.sum_worked_hours

    @api.depends(
        'sum_worked_hours',
        'l10n_ae_hours_worked',
        'contract_id.work_entry_source',
        'contract_id.wage'
    )
    def _compute_l10n_ae_basic_salary(self):
        for record in self:
            if record.contract_id.work_entry_source == 'calendar':
                record.l10n_ae_basic_salary = record.contract_id.wage
            else:
                record.l10n_ae_basic_salary = record.l10n_ae_hours_worked * (record.contract_id.wage / record.sum_worked_hours) if record.sum_worked_hours > 0 else 0

    @api.model
    def _l10n_ae_get_wps_formatted_amount(self, val):
        currency = self.env.ref('base.AED')
        return f'{currency.round(val):.{currency.decimal_places}f}'

    def _l10n_ae_get_wps_data(self):
        rows = []
        input_codes = [
            "HOUALLOWINP",
            "CONVALLOWINP",
            "MEDALLOWINP",
            "ANNUALPASSALLOWINP",
            "OVERTIMEALLOWINP",
            "OTALLOWINP",
            "LEAVEENCASHINP",
        ]
        inputs_dict = self._get_line_values(input_codes)

        for payslip in self:
            employee = payslip.employee_id
            unpaid_leave_days = payslip.worked_days_line_ids.filtered(
                lambda x: x.work_entry_type_id in payslip.struct_id.unpaid_work_entry_type_ids)
            unpaid_leave_day_count = sum(unpaid_leave_days.mapped('number_of_days'))
            evp_inputs = [inputs_dict[code][payslip.id]['total'] for code in input_codes]
            total_evp = sum(evp_inputs)

            rows.append([
                "EDR",
                (employee.identification_id or '').zfill(14),
                employee.bank_account_id.bank_id.l10n_ae_routing_code or '',
                employee.bank_account_id.acc_number or '',
                payslip.date_from.strftime('%Y-%m-%d'),
                payslip.date_to.strftime('%Y-%m-%d'),
                (payslip.date_to - payslip.date_from).days + 1,
                self._l10n_ae_get_wps_formatted_amount(payslip.net_wage - total_evp),
                self._l10n_ae_get_wps_formatted_amount(total_evp),
                unpaid_leave_day_count
            ])

            if not payslip.currency_id.is_zero(total_evp):
                rows.append([
                    "EVP",
                    (employee.identification_id or '').zfill(14),
                    employee.bank_account_id.bank_id.l10n_ae_routing_code or '',
                    *map(self._l10n_ae_get_wps_formatted_amount, evp_inputs)
                ])

        return rows

    def action_payslip_payment_report(self, export_format='l10n_ae_wps'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_payment_report_view_form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.ids,
                'default_payslip_run_id': self.payslip_run_id.id,
                'default_export_format': export_format,
            },
        }

    def compute_sheet(self):
        ae_payslips = self.filtered(lambda payslip: payslip.country_code == 'AE')
        ae_payslips._compute_l10n_ae_hourly_wage()
        ae_payslips._compute_l10n_ae_worked_values()
        ae_payslips._compute_l10n_ae_basic_salary()
        return super().compute_sheet()
