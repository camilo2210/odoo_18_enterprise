# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class HelpdeskMulticompanyWebsiteController(http.Controller):
    """Controller for the multi-company helpdesk teams portal page.

    Renders a public page at /helpdesk/teams showing all published
    helpdesk teams, filtered by the logged-in user's active company.
    Public (anonymous) users see all published teams grouped by company.
    """

    @http.route(
        '/helpdesk/teams',
        type='http',
        auth='public',
        website=True,
        sitemap=True,
    )
    def helpdesk_teams_page(self, **kwargs):
        """Render the helpdesk teams selector page.

        Business rules:
        - Only teams with is_published_on_portal=True are shown
        - Logged-in users see only teams from their active company
        - Public users see all published teams from all companies
        - Teams are grouped by company and ordered by sequence/name
        """
        user = request.env.user
        is_public_user = user._is_public()
        active_company = request.env.company

        # Base domain: only portal-published teams
        domain = [('is_published_on_portal', '=', True)]

        # For logged-in users, filter by their active company
        if not is_public_user:
            domain.append(('company_id', '=', active_company.id))
            _logger.info(
                'Helpdesk teams page accessed by user "%s" '
                '(active company: "%s", id=%s)',
                user.login,
                active_company.name,
                active_company.id,
            )
        else:
            _logger.info(
                'Helpdesk teams page accessed by public user'
            )

        # sudo() to bypass company-level record rules
        # We apply our own company filtering above
        teams = request.env['helpdesk.team'].sudo().search(
            domain, order='company_id, sequence, name'
        )

        # Ordered unique companies from the resulting teams
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
