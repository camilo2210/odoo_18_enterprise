import logging

from odoo import http
from odoo.http import request
from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk

_logger = logging.getLogger(__name__)


class WebsiteHelpdeskMulticompany(WebsiteHelpdesk):
    """Extiende el controlador de website_helpdesk para mostrar equipos
    de TODAS las compañías en un solo sitio web /helpdesk.

    Problema original: Odoo filtra los equipos por la compañía activa
    del website/sesión, mostrando solo los equipos de 1 compañía.

    Solución: Usar sudo() para saltar las reglas ir.rule de
    multi-compañía y obtener todos los equipos con helpdesk web activo.
    """

    @http.route()
    def website_helpdesk_teams(self, **kwargs):
        """Override: inyecta equipos de todas las compañías en /helpdesk.

        1. Ejecuta la lógica original con super() para mantener
           toda la preparación nativa del contexto.
        2. Reemplaza el recordset ``teams`` con uno que incluya
           equipos de todas las compañías vía sudo().
        """
        response = super().website_helpdesk_teams(**kwargs)

        # Solo modificar si estamos en la página de listado
        # y el contexto tiene la variable 'teams'
        if not hasattr(response, 'qcontext') or not response.qcontext:
            return response

        if 'teams' not in response.qcontext:
            return response

        # Detectar el campo booleano correcto para filtrar equipos
        # con helpdesk web activo (varía entre versiones de Odoo 18)
        HelpdeskTeam = request.env['helpdesk.team'].sudo()
        team_fields = HelpdeskTeam._fields

        if 'use_website_helpdesk_form' in team_fields:
            domain = [('use_website_helpdesk_form', '=', True)]
        elif 'use_website_helpdesk' in team_fields:
            domain = [('use_website_helpdesk', '=', True)]
        else:
            # Fallback: traer todos los equipos si no se encuentra el campo
            _logger.warning(
                'website_helpdesk_multicompany: No se encontró el campo '
                'use_website_helpdesk_form ni use_website_helpdesk. '
                'Se mostrarán todos los equipos.'
            )
            domain = []

        # Buscar equipos de TODAS las compañías, ordenados por compañía
        all_teams = HelpdeskTeam.search(
            domain,
            order='company_id, sequence, id',
        )

        if all_teams:
            response.qcontext['teams'] = all_teams

        _logger.info(
            'website_helpdesk_multicompany: Mostrando %d equipos de %d compañías',
            len(all_teams),
            len(all_teams.mapped('company_id')),
        )

        return response
