# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_multi_company = fields.Boolean(
        string='Allow Multiple Company Selection',
        compute='_compute_allow_multi_company',
        store=False,
        help='If enabled, user can select multiple companies at once'
    )

    @api.depends('groups_id')
    def _compute_allow_multi_company(self):
        """Compute if user has permission to select multiple companies"""
        multi_company_group = self.env.ref(
            'restrict_single_company.group_multi_company_selection',
            raise_if_not_found=False
        )
        for user in self:
            user.allow_multi_company = multi_company_group and multi_company_group in user.groups_id


    @api.model
    def get_user_company_restriction(self):
        """Return if current user can select multiple companies"""
        user = self.env.user
        
        # Check if user has the multi-company group
        multi_company_group = self.env.ref(
            'restrict_single_company.group_multi_company_selection',
            raise_if_not_found=False
        )
        
        allow_multi = multi_company_group and multi_company_group in user.groups_id
        
        return {
            'allow_multi_company': allow_multi,
            'company_ids': user.company_ids.ids,
            'current_company_id': user.company_id.id,
        }

        
        return super(ResUsers, self).write(vals)

