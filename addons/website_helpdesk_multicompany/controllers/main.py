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
        2. Si super() lanza un 404 (NotFound) porque el usuario portal
           no ve ningún equipo en su entorno, lo atrapamos.
        3. Reemplaza el recordset ``teams`` con uno que incluya
           equipos de todas las compañías vía sudo().
        """
        from werkzeug.exceptions import NotFound

        # Detectar el campo booleano correcto para filtrar equipos
        HelpdeskTeam = request.env['helpdesk.team'].sudo()
        team_fields = HelpdeskTeam._fields

        if 'use_website_helpdesk_form' in team_fields:
            domain = [('use_website_helpdesk_form', '=', True)]
        elif 'use_website_helpdesk' in team_fields:
            domain = [('use_website_helpdesk', '=', True)]
        else:
            domain = []

        all_teams = HelpdeskTeam.search(domain, order='company_id, sequence, id')

        if not all_teams:
            raise NotFound()

        try:
            response = super().website_helpdesk_teams(**kwargs)
            # Si super() hizo un redirect (porque creía que había solo 1 equipo), 
            # pero en realidad hay MÁS de 1 equipo globalmente, debemos evitar el redirect
            # y renderizar la lista completa.
            if response.status_code in (301, 302, 303) and len(all_teams) > 1:
                # Odoo normalmente usa 'website_helpdesk.team' para la lista de equipos.
                # Se requiere pasar 'team': recordset vacío para que la plantilla no falle con AttributeError.
                response = request.render("website_helpdesk.team", {'teams': all_teams, 'team': request.env['helpdesk.team'].sudo()})
            
            elif hasattr(response, 'qcontext') and response.qcontext:
                response.qcontext['teams'] = all_teams
                if 'team' not in response.qcontext or isinstance(response.qcontext['team'], bool):
                    response.qcontext['team'] = request.env['helpdesk.team'].sudo()

        except NotFound:
            # Si el usuario no veía equipos por multi-compañía, super() lanzó NotFound.
            # Renderizamos la plantilla de lista de equipos directamente.
            # Si solo hay 1 equipo a nivel global, redirigir a ese equipo:
            if len(all_teams) == 1:
                return request.redirect('/helpdesk/%s' % all_teams[0].id)
            
            # De lo contrario, mostrar la lista completa
            response = request.render("website_helpdesk.team", {'teams': all_teams, 'team': request.env['helpdesk.team'].sudo()})

        _logger.info(
            'website_helpdesk_multicompany: Mostrando %d equipos de %d compañías',
            len(all_teams),
            len(all_teams.mapped('company_id')),
        )

        return response

    @http.route([
        '/helpdesk/<string:team>',
        '/helpdesk/<string:team>/submit',
    ], type='http', auth="public", website=True, sitemap=False)
    def website_helpdesk_team(self, team, **kwargs):
        """Override del método nativo para evitar el error 403 (o 404) al acceder
        a un equipo de otra compañía desde el portal.

        Se reemplaza el convertidor <model("helpdesk.team"):team> por <string:team>
        para procesar el parámetro manualmente usando sudo() y saltar las
        reglas de multi-compañía (ir.rule) de helpdesk.team.
        """
        if isinstance(team, str):
            try:
                # Odoo normalmente pasa el string como "1-nombre-del-equipo" o "1"
                team_id = int(team.split('-')[0])
                team_sudo = request.env['helpdesk.team'].sudo().browse(team_id)
                if not team_sudo.exists():
                    raise request.not_found()
                # Reemplazamos el string con el recordset en modo sudo
                team = team_sudo
            except ValueError:
                raise request.not_found()
                
        # Llamamos al método original pasando el equipo en sudo().
        # El método original renderizará el formulario del equipo correctamente.
        return super().website_helpdesk_team(team, **kwargs)
