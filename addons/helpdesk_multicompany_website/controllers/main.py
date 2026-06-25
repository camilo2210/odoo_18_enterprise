# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


# Lazy import to avoid circular imports at module load time
def _get_helpdesk_controller():
    try:
        from odoo.addons.helpdesk.controllers.main import HelpdeskController
        return HelpdeskController
    except ImportError:
        return http.Controller


class HelpdeskMulticompanyController(http.Controller):
    """Multi-company helpdesk portal controller.

    Provides the /helpdesk/teams page (company selector).

    The 404 fix for individual team pages (/helpdesk/<slug>) is handled
    in the model layer (helpdesk_team.py) by overriding the method
    `can_access_from_current_website`, which is called by Odoo's model
    converter during URL routing. This means no controller override is
    needed for individual team pages — the model fix alone is sufficient.
    """

    @http.route(
        '/helpdesk/teams',
        type='http',
        auth='public',
        website=True,
        sitemap=True,
    )
    def helpdesk_teams_page(self, **kwargs):
        """Render the multi-company helpdesk team selector page.

        Business rules:
        - Only teams with is_published_on_portal=True are shown.
        - Logged-in users see only teams from their active company.
        - Public/anonymous users see all published teams grouped by company.
        - Teams are ordered by company, then sequence, then name.
        """
        user = request.env.user
        is_public_user = user._is_public()
        active_company = request.env.company

        domain = [('is_published_on_portal', '=', True)]

        if not is_public_user:
            domain.append(('company_id', '=', active_company.id))
            _logger.info(
                'Helpdesk teams page: user="%s", company="%s" (id=%s)',
                user.login, active_company.name, active_company.id,
            )
        else:
            _logger.info('Helpdesk teams page: anonymous user')

        # sudo() to read across companies; company filter applied above
        teams = request.env['helpdesk.team'].sudo().search(
            domain, order='company_id, sequence, name'
        )
        companies = teams.mapped('company_id')

        values = {
            'teams': teams,
            'companies': companies,
            'active_company': active_company,
            'is_public_user': is_public_user,
        }

        return request.render(
            'helpdesk_multicompany_website.helpdesk_teams_page',
            values,
        )
