import logging
import re

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk

_logger = logging.getLogger(__name__)


class WebsiteHelpdeskMulticompany(WebsiteHelpdesk):
    """Publica en /helpdesk los equipos de todas las compañías."""

    def _get_multicompany_teams(self):
        """Equipos con formulario web activo de todas las compañías."""
        return request.env['helpdesk.team'].sudo().search(
            [('use_website_helpdesk_form', '=', True)],
            order='company_id, id',
        )

    @http.route(
        ['/helpdesk', '/helpdesk/<string:team>'],
        type='http', auth='public', website=True, sitemap=True,
    )
    def website_helpdesk_teams(self, team=None, **kwargs):
        all_teams = self._get_multicompany_teams()
        if not all_teams:
            raise NotFound()

        # /helpdesk: lista con los equipos de todas las compañías.
        if not team:
            return request.render(
                'website_helpdesk.helpdesk_all_team', {'teams': all_teams},
            )

        # /helpdesk/<slug>: el id son los dígitos finales del slug.
        match = re.search(r'(\d+)$', str(team))
        if not match:
            raise NotFound()
        team_id = int(match.group(1))

        team_sudo = all_teams.filtered(lambda t: t.id == team_id)
        if not team_sudo:
            raise NotFound()

        # Solo se entra a equipos de las compañías del usuario.
        user_company_ids = request.env.user.company_ids.ids
        if team_sudo.company_id.id not in user_company_ids:
            return request.render(
                'website_helpdesk_multicompany.team_access_denied',
                {'team_name': team_sudo.name},
            )

        # Ampliar las compañías permitidas para que la ir.rule de
        # multi-compañía deje leer el equipo y sus campos SEO.
        request.update_context(allowed_company_ids=user_company_ids)
        team = request.env['helpdesk.team'].browse(team_id)
        return super().website_helpdesk_teams(team=team, **kwargs)
