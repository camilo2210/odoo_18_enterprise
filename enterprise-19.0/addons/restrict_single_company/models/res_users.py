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

    @api.constrains('company_ids')
    def _check_company_ids_restriction(self):
        """Validate that users without permission have only one company"""
        for user in self:
            # Skip for users with multi-company permission
            if user.allow_multi_company:
                continue
            
            # Skip for system/admin to avoid lockout
            if user.id == self.env.ref('base.user_admin').id:
                continue
                
            # Validate single company
            if len(user.company_ids) > 1:
                raise ValidationError(_(
                    'User "%s" does not have permission to have multiple companies assigned. '
                    'Please assign only one company or grant the "Allow Multiple Company Selection" permission.'
                ) % user.name)

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

    def write(self, vals):
        """Override write to handle company context updates"""
        # If updating allowed_company_ids from frontend
        if 'company_ids' in vals and request:
            for user in self:
                if user.id == self.env.uid:  # Current user
                    if not user.allow_multi_company:
                        # Ensure only one company in the list
                        company_ids = vals.get('company_ids')
                        if company_ids:
                            # Handle different formats
                            if isinstance(company_ids, list):
                                if len(company_ids) > 0:
                                    if isinstance(company_ids[0], (list, tuple)):
                                        # Format: [(6, 0, [ids])]
                                        actual_ids = company_ids[0][2] if len(company_ids[0]) > 2 else []
                                    else:
                                        # Format: [id1, id2, ...]
                                        actual_ids = company_ids
                                    
                                    if len(actual_ids) > 1:
                                        raise ValidationError(_(
                                            'You do not have permission to select multiple companies. '
                                            'Please select only one company at a time.'
                                        ))
        
        return super(ResUsers, self).write(vals)

