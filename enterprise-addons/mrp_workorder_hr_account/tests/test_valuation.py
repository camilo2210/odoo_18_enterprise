# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.mrp_account.tests.test_valuation_layers import TestMrpValuationCommon
from odoo.tests import Form

from datetime import datetime, timedelta


class TestMrpWorkorderHrValuation(TestMrpValuationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Jean Michel',
            'hourly_cost': 100,
        })

        cls.employee_center = cls.env['mrp.workcenter'].create({
            'name': 'Jean Michel\'s Center',
            'costs_hour': 10,
            'employee_ids': [(4, cls.employee.id)],
        })

        cls.bom.operation_ids = [(0, 0, {
            'name': 'Super Operation',
            'workcenter_id': cls.employee_center.id,
            'time_mode': 'manual',
            'time_cycle_manual': 60,
        })]

    def test_svl_includes_employee_cost(self):
        self.product1.categ_id.property_cost_method = 'fifo'

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom
        mo = mo_form.save()
        mo.action_confirm()

        with Form(mo) as mo_form:
            mo_form.qty_producing = 1

        # Register a productivity of one hour
        now = datetime.now()
        workorder = mo.workorder_ids
        self.env['mrp.workcenter.productivity'].create({
            'employee_id': self.employee.id,
            'workcenter_id': self.employee_center.id,
            'workorder_id': workorder.id,
            'date_start': now,
            'date_end': now + timedelta(hours=1),
            'loss_id': self.env.ref('mrp.block_reason7').id,
        })
        workorder.button_done()

        mo.button_mark_done()

        self.assertEqual(self.product1.stock_valuation_layer_ids.remaining_value, 110, 'Workcenter cost (10) + Employee cost (100)')

    @freeze_time('2020-01-01 08:00:00')
    def test_cost_calculation_multiple_employees_same_workcenter(self):
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.standard_price = 75
        self.employee_center.costs_hour = 35
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom
        mo = mo_form.save()
        mo.action_confirm()

        with Form(mo) as mo_form:
            mo_form.qty_producing = 1

        employee1, employee2 = self.employee, self.env['hr.employee'].create({
            'name': 'employee 2',
            'hourly_cost': 40
        })
        employee1.hourly_cost = 15
        workorder = mo.workorder_ids
        ymd = {'year': 2020, 'month': 1, 'day': 1}
        # emp1 works (08:00 until 09:30) and (11:30 until 12:00)
        self.env['mrp.workcenter.productivity'].create([{
            'employee_id': employee1.id,
            'workcenter_id': self.employee_center.id,
            'workorder_id': workorder.id,
            'date_start': start,
            'date_end': end,
            'loss_id': self.ref('mrp.block_reason7'),
        } for start, end in (
            (datetime(**ymd, hour=8), datetime(**ymd, hour=9, minute=30)),
            (datetime(**ymd, hour=11, minute=30), datetime(**ymd, hour=12)),
        )])
        # emp2 works (08:30:00 until 09:30) and (10:30 until 11:30)
        self.env['mrp.workcenter.productivity'].create([{
            'employee_id': employee2.id,
            'workcenter_id': self.employee_center.id,
            'workorder_id': workorder.id,
            'date_start': start,
            'date_end': end,
            'loss_id': self.ref('mrp.block_reason7'),
        } for start, end in (
            (datetime(**ymd, hour=8, minute=30), datetime(**ymd, hour=9, minute=30)),
            (datetime(**ymd, hour=10, minute=30), datetime(**ymd, hour=11, minute=30)),
        )])
        # => workcenter is operated from: [08:00 - 09:30] and [10:30 - 12:00] = 180 minutes
        # we should get a workcenter cost like: ($35 / hour * 1.5 hours) + ($35 / hour * 1.5 hours) = $105.0
        workorder.button_done()
        mo.button_mark_done()
        finished_product_svl = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)])
        # SVL value derived like:
        #   emp1 total cost        + emp2 total cost        + workcenter costs
        # = ($15 / hour * 2 hours) + ($40 / hour * 2 hours) + ($105.0)
        # = $215.0
        self.assertRecordValues(
            finished_product_svl,
            [{'value': 215.0}],
        )
