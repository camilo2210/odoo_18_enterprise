# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.addons.helpdesk_website.controllers.main import HelpdeskWebsiteController

_logger = logging.getLogger(__name__)


class HelpdeskMulticompanyPortalController(HelpdeskWebsiteController):
    @http.route(
        ['/helpdesk', '/helpdesk/page/<int:page>'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def helpdesk_index(self, page=1, **kwargs):
        _logger.info(
            "helpdesk_index multicompany: uid=%s, website=%s",
            request.uid,
            request.website.id if request.website else None,
        )

        user = request.env.user
        if user._is_public():
            _logger.info("Usuario público: se conserva comportamiento nativo.")
            return super().helpdesk_index(page=page, **kwargs)

        allowed_company_ids = self._get_portal_user_company_ids(user)

        _logger.info(
            "Usuario portal uid=%s, compañías permitidas=%s",
            user.id,
            allowed_company_ids,
        )

        teams = self._get_multicompany_helpdesk_teams(allowed_company_ids)

        teams_by_company = {}
        for team in teams:
            company = team.company_id
            if company not in teams_by_company:
                teams_by_company[company] = []
            teams_by_company[company].append(team)

        values = {
            'teams': teams,
            'teams_by_company': teams_by_company,
            'multicompany_mode': True,
            'page_name': 'helpdesk',
        }
        return request.render(
            'helpdesk_multicompany_portal.portal_helpdesk_multicompany_index',
            values,
        )

    def _get_portal_user_company_ids(self, user):
        partner = user.partner_id

        try:
            if hasattr(partner, 'company_ids') and partner.company_ids:
                return partner.company_ids.ids
        except Exception as exc:
            _logger.warning("Error leyendo partner.company_ids: %s", exc)

        if partner.company_id:
            return [partner.company_id.id]

        try:
            if user.company_ids:
                return user.company_ids.ids
        except Exception as exc:
            _logger.warning("Error leyendo user.company_ids: %s", exc)

        if user.company_id:
            return [user.company_id.id]

        return []

    def _get_multicompany_helpdesk_teams(self, company_ids):
        if not company_ids:
            return request.env['helpdesk.team'].browse([])

        domain = [
            ('use_website_helpdesk_form', '=', True),
            ('company_id', 'in', company_ids),
        ]

        teams = (
            request.env['helpdesk.team']
            .with_context(allowed_company_ids=company_ids)
            .sudo()
            .search(domain, order='company_id asc, name asc')
        )

        _logger.info("Equipos visibles: %s", teams.ids)
        return teams