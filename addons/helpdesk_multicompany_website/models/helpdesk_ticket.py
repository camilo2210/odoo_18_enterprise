# -*- coding: utf-8 -*-
import logging

from odoo import models, api, _
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # =========================================================================
    # CONSTRAINT — Seguridad multicompañía
    # =========================================================================

    @api.constrains('team_id', 'company_id')
    def _check_company_team_consistency(self):
        """Evita tickets cross-company: ticket.company debe coincidir con team.company."""
        for ticket in self:
            if not ticket.team_id or not ticket.company_id:
                continue
            if not ticket.team_id.company_id:
                continue
            if ticket.company_id != ticket.team_id.company_id:
                raise ValidationError(_(
                    'El ticket "%(ticket)s" no puede crearse en la compañía '
                    '"%(tc)s" porque el equipo "%(team)s" pertenece a '
                    '"%(ec)s". Los tickets deben coincidir con la compañía '
                    'de su equipo.',
                    ticket=ticket.name or _('Nuevo'),
                    tc=ticket.company_id.name,
                    team=ticket.team_id.name,
                    ec=ticket.team_id.company_id.name,
                ))

    # =========================================================================
    # SERVICIO — Creación de ticket desde el portal
    # =========================================================================

    @api.model
    def create_portal_mc_ticket(self, team_id, name, partner_name,
                                partner_email, description='',
                                ticket_type_id=None):
        """Crea un ticket desde el portal multicompañía.

        Este método centraliza la lógica de creación de tickets del portal
        y es el único punto donde se eleva el privilegio para operaciones
        de escritura, siguiendo el principio de mínimo privilegio:

        - La búsqueda del equipo NO usa sudo: el ORM aplica las record rules
          y la ACL configuradas en security/, garantizando que solo equipos
          publicados sean accesibles.
        - La búsqueda/creación del partner SÍ usa sudo de forma acotada:
          es técnicamente necesario porque el usuario público no tiene acceso
          de lectura/escritura sobre res.partner, y es el patrón estándar
          de todos los flujos de portal en Odoo (website_sale, helpdesk nativo).
          El alcance es mínimo: solo search + create con campos específicos.
        - La creación del ticket se hace con with_company() para garantizar
          que el ticket quede asignado a la compañía correcta del equipo.

        Args:
            team_id (int): ID del equipo de helpdesk.
            name (str): Asunto del ticket.
            partner_name (str): Nombre del solicitante.
            partner_email (str): Email del solicitante.
            description (str): Descripción detallada (opcional).
            ticket_type_id (int|None): ID del tipo de ticket (opcional).

        Returns:
            helpdesk.ticket: El ticket creado.

        Raises:
            AccessError: Si el equipo no existe o no está publicado en portal.
            ValidationError: Si los datos son inválidos.
        """
        # ------------------------------------------------------------------
        # 1. Obtener el equipo SIN sudo → el ORM aplica record rules + ACL
        #    Solo equipos con is_published_on_portal=True son visibles para
        #    el usuario público/portal (garantizado por security/).
        # ------------------------------------------------------------------
        team = self.env['helpdesk.team'].browse(team_id)
        if not team.exists():
            raise AccessError(_('El equipo de mesa de ayuda no existe.'))
        if not team.is_published_on_portal:
            raise AccessError(_(
                'El equipo "%(team)s" no está disponible en el portal.',
                team=team.name,
            ))

        # ------------------------------------------------------------------
        # 2. Buscar o crear el partner CON sudo acotado.
        #    JUSTIFICACIÓN: El usuario público (base.group_public) no tiene
        #    acceso de lectura/escritura en res.partner por diseño de Odoo.
        #    Este es el único punto de elevación de privilegio y sigue el
        #    mismo patrón que el controlador nativo de helpdesk de Odoo.
        #    Alcance: solo email + nombre, sin acceso a otros datos del partner.
        # ------------------------------------------------------------------
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search(
            [('email', '=ilike', partner_email.strip())], limit=1
        )
        if not partner:
            partner = Partner.create({
                'name': partner_name.strip(),
                'email': partner_email.strip(),
            })
            _logger.info(
                'Portal MC: partner creado email="%s" (id=%s)',
                partner_email, partner.id,
            )

        # ------------------------------------------------------------------
        # 3. Preparar valores del ticket
        # ------------------------------------------------------------------
        vals = {
            'name': name.strip(),
            'description': description.strip() if description else '',
            'team_id': team.id,
            'company_id': team.company_id.id,
            'partner_id': partner.id,
            'partner_name': partner_name.strip(),
            'partner_email': partner_email.strip(),
        }

        if ticket_type_id:
            try:
                vals['ticket_type_id'] = int(ticket_type_id)
            except (ValueError, TypeError):
                pass

        # Si el usuario está autenticado (no público), asignarlo
        if not self.env.user._is_public():
            vals['user_id'] = self.env.user.id

        # ------------------------------------------------------------------
        # 4. Crear el ticket con with_company() para garantizar la compañía.
        #    NO se usa sudo(): el usuario portal tiene derechos de creación
        #    en helpdesk.ticket a través de la ACL nativa del módulo helpdesk.
        # ------------------------------------------------------------------
        ticket = self.with_company(team.company_id).create(vals)

        _logger.info(
            'Portal MC: ticket #%s "%s" creado en equipo "%s" '
            '(company: %s) por "%s" <%s>',
            ticket.id, ticket.name, team.name,
            team.company_id.name, partner_name, partner_email,
        )
        return ticket
