# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Appointment(models.Model):
     _name = 'support.appointment'
     _description = 'Modelo para el agendamiento de citas'

     date = fields.Date(
          string='Fecha de la Cita',
          required=True,
          help='Fecha en la que requiere la cita'
     )

     time = fields.Selection([
          ('0', '9:00'),('1', '9:30'),('2', '10:00'),('3', '10:30'),('4', '11:00'),('5', '11:30'),('6', '12:00'),('7', '12:30'),('8', '13:00') 
     ], string='Hora de la Cita', required=True,help='Hora de la cita en intervalos de 30 minutos')

     name = fields.Char('Nombre', required=True, help='Nombre de la persona que va solicitar la cita')

     mail = fields.Char('E-mail', required=True)

     phone = fields.Char('Titulo', required=True)

     description = fields.Char('Descripcion', required=True)

     service_ids = fields.Many2one(
         string='Servicio',
         comodel_name='support.service',
         ondelete='restrict',
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

