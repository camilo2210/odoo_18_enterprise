# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.tests import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ae'),
            structure=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure'),
            structure_type=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure_type'),
            contract_fields={
                'wage': 40000.0,
                'l10n_ae_housing_allowance': 400.0,
                'l10n_ae_transportation_allowance': 220.0,
                'l10n_ae_other_allowances': 100.0,
                'l10n_ae_is_dews_applied': True,
            }
        )

        cls.work_entry_types = {
            entry_type.code: entry_type
            for entry_type in cls.env['hr.work.entry.type'].search([])
        }

    @classmethod
    def _create_worked_days(cls, name=False, code=False, number_of_days=0, number_of_hours=0):
        return Command.create({
            'name': name,
            'work_entry_type_id': cls.work_entry_types[code].id,
            'code': code,
            'number_of_days': number_of_days,
            'number_of_hours': number_of_hours,
        })

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 40720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 35352.0}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self._add_other_inputs(payslip, {
            'l10n_ae_hr_payroll.input_salary_arrears': 1000.0,
            'l10n_ae_hr_payroll.input_other_earnings': 2000.0,
            'l10n_ae_hr_payroll.input_salary_deduction': 500.0,
            'l10n_ae_hr_payroll.input_other_deduction': 200.0,
            'l10n_ae_hr_payroll.l10n_ae_input_overtime_allowance': 300,
            'l10n_ae_hr_payroll.input_bonus_earnings': 400,
            'l10n_ae_hr_payroll.l10n_ae_input_other_allowance': 600,
            'l10n_ae_hr_payroll.input_airfare_allowance_earnings': 700,
        })
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'SALARY_ARREARS': 1000.0, 'OTHER_EARNINGS': 2000.0, 'SALARY_DEDUCTIONS': -500.0, 'OTHER_DEDUCTIONS': -200.0, 'OVERTIMEALLOWINP': 300.0, 'BONUS': 400.0, 'OTALLOWINP': 600.0, 'AIRFARE_ALLOWANCE': 700.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 45720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 39652.0}
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_service_salary_rule_1(self):
        """
        Test the end of service salary rule calculation.
        The rule should consider the full 30 days compensation after completing the 6th year, not the 5th.
        """
        employee_1 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
        })
        contract_1 = self.env['hr.contract'].create({
            'name': 'Test Contract 1',
            'employee_id': employee_1.id,
            'wage': 15_000.0,
            'state': 'open',
            'date_start': date(2014, 6, 4),
        })

        departure_notice_1 = self.env['hr.departure.wizard'].create({
            'employee_id': employee_1.id,
            'departure_date': date(2017, 2, 19),
            'departure_description': 'foo',
        })
        departure_notice_1.with_context(toggle_active=True).action_register_departure()

        payslip_1 = self._generate_payslip(
            date(2017, 2, 1),
            date(2017, 2, 28),
            employee_id=employee_1.id,
            contract_id=contract_1.id,
        )

        self.assertEqual(payslip_1._get_line_values(['EOS'])['EOS'][payslip_1.id]['total'], 28_432.0, "End of Service calculation is incorrect")

    def test_end_of_service_salary_rule_2(self):
        employee_2 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
        })
        contract_2 = self.env['hr.contract'].create({
            'name': 'Test Contract 1',
            'employee_id': employee_2.id,
            'wage': 15_000.0,
            'state': 'open',
            'date_start': date(2019, 7, 22),
        })

        departure_notice_2 = self.env['hr.departure.wizard'].create({
            'employee_id': employee_2.id,
            'departure_date': date(2025, 1, 8),
            'departure_description': 'foo',
        })
        departure_notice_2.with_context(toggle_active=True).action_register_departure()

        payslip_2 = self._generate_payslip(
            date(2025, 1, 1),
            date(2025, 1, 31),
            employee_id=employee_2.id,
            contract_id=contract_2.id,
        )

        self.assertEqual(payslip_2._get_line_values(['EOS'])['EOS'][payslip_2.id]['total'], 57_365.0, "End of Service calculation is incorrect")

    def test_end_of_service_salary_rule_3(self):
        employee_3 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
        })
        contract_3 = self.env['hr.contract'].create({
            'name': 'Test Contract 1',
            'employee_id': employee_3.id,
            'wage': 15_000.0,
            'state': 'open',
            'date_start': date(2018, 7, 22),
        })

        departure_notice_3 = self.env['hr.departure.wizard'].create({
            'employee_id': employee_3.id,
            'departure_date': date(2025, 1, 8),
            'departure_description': 'foo',
        })
        departure_notice_3.with_context(toggle_active=True).action_register_departure()

        payslip_3 = self._generate_payslip(
            date(2025, 1, 1),
            date(2025, 1, 31),
            employee_id=employee_3.id,
            contract_id=contract_3.id,
        )

        self.assertEqual(payslip_3._get_line_values(['EOS'])['EOS'][payslip_3.id]['total'], 74_449.0, "End of Service calculation is incorrect")

    def test_payslip_attendance_1(self):
        if self.env['ir.module.module']._get('hr_payroll_attendance').state != 'installed':
            self.skipTest("Skipping test because hr_payroll_attendance is not installed.")

        self.employee.country_id = False
        self.contract.write({
            'date_start': '2025-01-01',
            'work_entry_source': 'attendance',
            'wage': 5000,
            'wage_type': 'monthly',
            'l10n_ae_housing_allowance': 2000,
            'l10n_ae_transportation_allowance': 1000,
            'l10n_ae_other_allowances': 100,
            'l10n_ae_is_dews_applied': False,
        })

        worked_days_vals = [
            {'name': 'Unpaid', 'code': 'LEAVE90', 'number_of_hours': 16, 'number_of_days': 2},
            {'name': 'Paid Time Off', 'code': 'LEAVE120', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Sick Leave 50', 'code': 'SICKLEAVE50', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Out of Contract', 'code': 'OUT', 'number_of_hours': 32, 'number_of_days': 4},
            {'name': 'Attendance', 'code': 'WORK100', 'number_of_hours': 88, 'number_of_days': 11},
        ]

        payslip = self._generate_payslip('2025-07-01', '2025-07-31')
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals],
        })
        payslip.compute_sheet()
        payslip_results = {
            'BASIC': 2391.30,
            'HOUALLOW': 956.52,
            'TRAALLOW': 478.26,
            'OTALLOW': 47.83,
            'EOSP': 188.73,
            'ALP': 436.76,
            'AEPAID': 1056.48,
            'AESPAID50': 528.24,
            'GROSS': 5458.63,
            'NET': 5458.63,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_attendance_2(self):
        if self.env['ir.module.module']._get('hr_payroll_attendance').state != 'installed':
            self.skipTest("Skipping test because hr_payroll_attendance is not installed.")

        self.employee.country_id = False
        self.contract.write({
            'date_start': '2025-01-01',
            'work_entry_source': 'attendance',
            'wage': 5000,
            'hourly_wage': 44.02,
            'wage_type': 'hourly',
            'l10n_ae_housing_allowance': 2000,
            'l10n_ae_transportation_allowance': 1000,
            'l10n_ae_other_allowances': 100,
            'l10n_ae_is_dews_applied': False,
        })

        worked_days_vals = [
            {'name': 'Unpaid', 'code': 'LEAVE90', 'number_of_hours': 16, 'number_of_days': 2},
            {'name': 'Paid Time Off', 'code': 'LEAVE120', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Sick Leave 50', 'code': 'SICKLEAVE50', 'number_of_hours': 24, 'number_of_days': 3},
            {'name': 'Out of Contract', 'code': 'OUT', 'number_of_hours': 32, 'number_of_days': 4},
            {'name': 'Attendance', 'code': 'WORK100', 'number_of_hours': 88, 'number_of_days': 11},
        ]

        payslip = self._generate_payslip('2025-06-01', '2025-06-30')
        payslip.write({
            "worked_days_line_ids": [self._create_worked_days(**vals) for vals in worked_days_vals]
        })
        payslip.compute_sheet()
        payslip_results = {
            'BASIC': 2391.30,
            'EOSP': 188.73,
            'ALP': 436.76,
            'AEPAID': 1056.48,
            'AESPAID50': 528.24,
            'GROSS': 3976.02,
            'NET': 3976.02,
        }
        self._validate_payslip(payslip, payslip_results)
