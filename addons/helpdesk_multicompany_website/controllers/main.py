# -*- coding: utf-8 -*-
import logging

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class HelpdeskMCController(http.Controller):
    """
    Controlador del Portal Multicompañía de Helpdesk.

    POLÍTICA DE SEGURIDAD:
    - Este controlador NO usa sudo() en ningún punto.
    - El control de acceso a lectura se delega a las ACL y record rules
      definidas en security/ir.model.access.csv y security/helpdesk_mc_security.xml.
    - La creación de tickets se delega al método de servicio
      helpdesk.ticket.create_portal_mc_ticket() que encapsula la lógica
      de negocio y el único sudo() justificado (para res.partner).

    Rutas:
      GET  /helpdesk/teams              → selector de equipos por compañía
      GET  /helpdesk/mc/<team_id>       → formulario de creación de ticket
      POST /helpdesk/mc/<team_id>/submit → procesa y crea el ticket
    """

    # =========================================================================
    # RUTA 1: /helpdesk/teams — Página de selección de equipos
    # =========================================================================

    @http.route(
        '/helpdesk/teams',
        type='http',
        auth='public',
        website=True,
        sitemap=True,
    )
    def helpdesk_teams_page(self, **kwargs):
        """
        Muestra los equipos de helpdesk publicados, agrupados por compañía.

        Sin sudo(): el ORM aplica automáticamente las record rules que
        restringen la visibilidad a equipos con is_published_on_portal=True.
        El filtro por compañía activa se aplica para usuarios autenticados.
        """
        user = request.env.user
        is_public = user._is_public()

        # Dominio base: las record rules ya filtran por is_published_on_portal=True.
        # Para usuarios autenticados, mostramos los equipos de TODAS las
        # compañías a las que tienen acceso (user.company_ids).
        domain = []
        if not is_public:
            domain.append(('company_id', 'in', user.company_ids.ids))

        # Sin sudo: el ORM aplica ACL + record rules.
        # IMPORTANTE: Para que la regla nativa multi-compañía de Odoo permita ver
        # los equipos de las otras compañías a las que el usuario tiene acceso,
        # inyectamos sus company_ids en el contexto (allowed_company_ids).
        TeamsEnv = request.env['helpdesk.team']
        if not is_public:
            TeamsEnv = TeamsEnv.with_context(allowed_company_ids=user.company_ids.ids)

        teams = TeamsEnv.search(domain, order='company_id, sequence, name')
        companies = teams.mapped('company_id')

        return request.render(
            'helpdesk_multicompany_website.helpdesk_teams_page',
            {
                'teams': teams,
                'companies': companies,
                'is_public': is_public,
                'user_companies_count': len(user.company_ids) if not is_public else 0,
            },
        )

    # =========================================================================
    # RUTA 2: /helpdesk/mc/<team_id> — Formulario de ticket (GET)
    # =========================================================================

    @http.route(
        '/helpdesk/mc/<int:team_id>',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def helpdesk_ticket_form(self, team_id, error=None, success=False, **kwargs):
        """
        Renderiza el formulario de creación de ticket para un equipo.

        Sin sudo(): el equipo se busca con browse() + verificación de acceso.
        Si el usuario no tiene acceso al equipo (no publicado o no existe),
        el ORM levantará AccessError que se convierte en 404.

        Usa /helpdesk/mc/<int:team_id> (ID entero) en lugar del slug nativo
        para evitar completamente el enrutador de Odoo que aplica restricciones
        de website_id y causa 404 en entornos multicompañía sin subdominios.
        """
        # browse() sin sudo: el ORM verificará el acceso vía ACL + record rules.
        # Añadimos allowed_company_ids para que el usuario pueda acceder a equipos
        # de sus otras compañías sin ser bloqueado por la regla multi-compañía nativa.
        user = request.env.user
        TeamsEnv = request.env['helpdesk.team']
        if not user._is_public():
            TeamsEnv = TeamsEnv.with_context(allowed_company_ids=user.company_ids.ids)

        team = TeamsEnv.browse(team_id)

        try:
            # Verificar acceso: si el equipo no es visible (record rule),
            # exists() o el acceso al campo lanzará un error controlado
            if not team.exists() or not team.is_published_on_portal:
                return request.not_found()
        except AccessError:
            return request.not_found()

        # Tipos de ticket: lectura defensiva.
        # helpdesk.ticket.type puede no existir si el submódulo no está instalado.
        ticket_types = False
        if 'helpdesk.ticket.type' in request.env:
            try:
                ticket_types = request.env['helpdesk.ticket.type'].search(
                    [('team_ids', 'in', [team.id])],
                    order='name',
                )
            except Exception:
                ticket_types = False

        return request.render(
            'helpdesk_multicompany_website.helpdesk_ticket_form_page',
            {
                'team': team,
                'ticket_types': ticket_types,
                'error': error or {},
                'success': success,
                'default_values': kwargs,
            },
        )

    # =========================================================================
    # RUTA 3: /helpdesk/mc/<team_id>/submit — Procesa el formulario (POST)
    # =========================================================================

    @http.route(
        '/helpdesk/mc/<int:team_id>/submit',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def helpdesk_ticket_submit(self, team_id, **post):
        """
        Valida los datos del formulario y delega la creación al modelo.

        Sin sudo() en el controlador: la validación de negocio y la creación
        del ticket se realizan a través del método de servicio del modelo
        helpdesk.ticket.create_portal_mc_ticket(), que gestiona la elevación
        de privilegios de forma controlada y documentada.
        """
        # --- Validación de campos obligatorios ---
        error = {}
        name = (post.get('name') or '').strip()
        description = (post.get('description') or '').strip()
        partner_email = (post.get('partner_email') or '').strip()
        partner_name = (post.get('partner_name') or '').strip()

        if not name:
            error['name'] = _('El asunto es obligatorio.')
        if not partner_email:
            error['partner_email'] = _('El correo electrónico es obligatorio.')
        if not partner_name:
            error['partner_name'] = _('El nombre es obligatorio.')

        refill_values = {
            k: post.get(k, '')
            for k in ['name', 'description', 'partner_email',
                      'partner_name', 'ticket_type_id']
        }

        if error:
            return self.helpdesk_ticket_form(
                team_id, error=error, **refill_values
            )

        # --- Delegar creación al modelo (sin sudo en el controlador) ---
        try:
            request.env['helpdesk.ticket'].create_portal_mc_ticket(
                team_id=team_id,
                name=name,
                partner_name=partner_name,
                partner_email=partner_email,
                description=description,
                ticket_type_id=post.get('ticket_type_id'),
            )
        except AccessError as e:
            _logger.warning('Portal MC: AccessError al crear ticket: %s', str(e))
            return request.not_found()
        except (ValidationError, Exception) as e:
            _logger.error('Portal MC: error al crear ticket: %s', str(e))
            return self.helpdesk_ticket_form(
                team_id,
                error={'_global': str(e)},
                **refill_values,
            )

        # --- Redirigir con flag de éxito ---
        return request.redirect('/helpdesk/mc/%d?success=1' % team_id)
