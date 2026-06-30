import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            team_id = vals.get('team_id')
            if team_id:
                # Utilizamos sudo() para sortear restricciones temporales de lectura si el formulario web
                # está procesando la creación bajo el contexto estricto de la compañía del website.
                team = self.env['helpdesk.team'].sudo().browse(team_id)
                if team.exists() and team.company_id:
                    # Garantizar invariablemente que el ticket pertenezca a la compañía del equipo seleccionado.
                    # Se sobrescribe cualquier valor de company_id inyectado por defecto desde el portal.
                    vals['company_id'] = team.company_id.id
                    _logger.info("Asignando ticket a la compañía %s correspondiente al equipo %s", team.company_id.name, team.name)
        
        return super(HelpdeskTicket, self).create(vals_list)
