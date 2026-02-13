# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Service(models.Model):
     _name = 'support.service'
     _description = 'Modelo para los servicios'

     name = fields.Char('Nombre', required=True)

     description = fields.Char('Descripcion', required=True)

appointment_ids= fields.One2many(
    string='appointment',
    comodel_name='support.appointment',
    inverse_name='inverse_field',
)



# class personalized_addon(models.Model):
#     _name = 'personalized_addon.personalized_addon'
#     _description = 'personalized_addon.personalized_addon'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

