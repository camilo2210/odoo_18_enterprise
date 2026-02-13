# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Incidence(models.Model):
     _name = 'support.incidence'
     _description = 'Modelo para la gestion de incidencias'


     title = fields.Char('Titulo', required=True)

     description = fields.Html(
          string='Descripcion',
          help='Detalle brevemente la incidencia ocurrida',
          required=True)

     priority = fields.Integer(
          string='Prioridad',
          default=0,
          help='Establece un valor mayor o igual a 10'
     )

     urgent = fields.Selection(
          [('0', 'No'), ('1', 'Si')], 
          string='Urgente', 
          readonly=True)
     
     location = fields.Selection([
          ('0', 'Aula 1'), ('1', 'Aula 2') 
     ], string='Ubicación')

     closed = fields.Boolean('Cerrada')

     photo = fields.Image(
          string='Foto', 
          max_wiheight=250
          )

     file = fields.Binary('Archivo Adjunto')

     creation_date = fields.Datetime(
          string='Fecha de Creacion', 
          default=fields.Datetime.now
          )
     
     modify_date = fields.Date(
          string='Fecha de modificación',
          default=fields.Datetime.now
          )


#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

