# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.http import request
from odoo.addons.helpdesk_website.controllers.main import HelpdeskWebsiteController

_logger = logging.getLogger(__name__)


class HelpdeskMulticompanyPortalController(HelpdeskWebsiteController):
    """
    Extiende el controlador nativo de helpdesk_website para mostrar,
    en el sitio web principal (multicompany), todos los equipos de helpdesk
    de todas las compañías que el usuario portal tenga asignadas.

    NO se sobreescribe la ruta de envío de tickets: el formulario nativo
    de cada equipo usa su propio endpoint y asigna la compañía del equipo.
    Solo se interviene el listado de equipos visibles.
    """

    @http.route(
        ['/helpdesk', '/helpdesk/page/<int:page>'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def helpdesk_index(self, page=1, **kwargs):
        """
        Override del listado de equipos. En modo multicompany + sitio web principal,
        muestra los equipos de TODAS las compañías accesibles para el usuario actual.
        """
        _logger.info(
            "helpdesk_index multicompany: uid=%s, website=%s",
            request.uid,
            request.website.id if request.website else None,
        )

        current_website = request.website
        if not current_website:
            _logger.warning("No hay sitio web en el contexto de la petición.")
            return super().helpdesk_index(page=page, **kwargs)

        user = request.env.user
        is_public = user._is_public()

        if is_public:
            _logger.info("Usuario público: delegando al comportamiento nativo.")
            return super().helpdesk_index(page=page, **kwargs)

        partner = user.partner_id
        allowed_company_ids = self._get_portal_user_company_ids(user, partner)

        _logger.info(
            "Usuario portal uid=%s, partner=%s, compañías accesibles=%s",
            user.id,
            partner.id,
            allowed_company_ids,
        )

        teams = self._get_multicompany_helpdesk_teams(allowed_company_ids)

        if not teams:
            _logger.warning(
                "No se encontraron equipos de helpdesk publicados para las "
                "compañías del usuario uid=%s: %s",
                user.id,
                allowed_company_ids,
            )

        teams_by_company = {}
        for team in teams:
            company = team.company_id
            if company not in teams_by_company:
                teams_by_company[company] = []
            teams_by_company[company].append(team)

        _logger.info(
            "Equipos agrupados por compañía: %s",
            {c.name: len(t) for c, t in teams_by_company.items()},
        )

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

    # ─────────────────────────────────────────────────────────────────────────
    # Métodos de servicio — lógica de negocio aislada del rendering
    # ─────────────────────────────────────────────────────────────────────────

    def _get_portal_user_company_ids(self, user, partner):
        """
        Devuelve la lista de IDs de compañías accesibles para el usuario portal.

        Prioridad:
        1. partner.company_ids  → acceso multi-compañía explícito
        2. partner.company_id   → compañía principal del partner
        3. user.company_id      → compañía activa del usuario (fallback)
        """
        try:
            if hasattr(partner, 'company_ids') and partner.company_ids:
                ids = partner.company_ids.ids
                _logger.info("Compañías del partner (company_ids): %s", ids)
                return ids
        except Exception as exc:
            _logger.warning("Error leyendo partner.company_ids: %s", exc)

        if partner.company_id:
            _logger.info("Compañía principal del partner: %s", partner.company_id.id)
            return [partner.company_id.id]

        if user.company_id:
            _logger.info("Compañía del usuario: %s", user.company_id.id)
            return [user.company_id.id]

        _logger.warning("No se encontraron compañías para el usuario uid=%s", user.id)
        return []

    def _get_multicompany_helpdesk_teams(self, company_ids):
        """
        Recupera todos los equipos de helpdesk con formulario web habilitado
        que pertenezcan a alguna de las compañías indicadas.

        Usa sudo() solo para lectura cross-company, con filtro explícito
        por company_ids — no se alteran record rules del modelo.
        """
        if not company_ids:
            return request.env['helpdesk.team'].sudo().browse([])

        try:
            domain = [
                ('use_website_helpdesk_form', '=', True),
                ('company_id', 'in', company_ids),
            ]

            teams = (
                request.env['helpdesk.team']
                .sudo()
                .search(domain, order='company_id asc, name asc')
            )

            _logger.info(
                "Equipos encontrados para compañías %s: %s",
                company_ids,
                teams.ids,
            )
            return teams

        except Exception as exc:
            _logger.exception(
                "Error inesperado obteniendo equipos de helpdesk para compañías %s: %s",
                company_ids,
                exc,
            )
            return request.env['helpdesk.team'].sudo().browse([])