# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    # -------------------------------------------------------------------------
    # FIELDS — Portal Multi-Company Configuration
    # -------------------------------------------------------------------------

    is_published_on_portal = fields.Boolean(
        string='Publicar en Portal Multicompañía',
        default=False,
        help=(
            'Si está activo, este equipo se mostrará en la página centralizada '
            'de equipos de mesa de ayuda del sitio web (/helpdesk/teams). '
            'El equipo solo será visible para usuarios cuya compañía activa '
            'coincida con la compañía de este equipo.'
        ),
    )

    website_icon = fields.Selection(
        selection=[
            ('fa-shopping-cart', 'Carrito de Compras'),
            ('fa-building', 'Edificio / Empresa'),
            ('fa-cubes', 'Cubos / Logística'),
            ('fa-users', 'Personas / RRHH'),
            ('fa-cogs', 'Engranajes / IT'),
            ('fa-truck', 'Camión / Transporte'),
            ('fa-wrench', 'Llave / Mantenimiento'),
            ('fa-headphones', 'Audífonos / Soporte'),
            ('fa-envelope', 'Sobre / Correo'),
            ('fa-shield', 'Escudo / Seguridad'),
            ('fa-life-ring', 'Salvavidas / Ayuda'),
            ('fa-laptop', 'Laptop / Tecnología'),
            ('fa-medkit', 'Kit Médico / Salud'),
            ('fa-graduation-cap', 'Birrete / Educación'),
            ('fa-money', 'Dinero / Finanzas'),
            ('fa-file-text-o', 'Documento / Archivo'),
            ('fa-gavel', 'Martillo / Legal'),
            ('fa-pie-chart', 'Gráfico / Reportes'),
        ],
        string='Ícono del Portal',
        default='fa-users',
        help=(
            'Ícono FontAwesome que se mostrará en la tarjeta de este equipo '
            'dentro de la página del portal web.'
        ),
    )

    website_description = fields.Text(
        string='Descripción del Portal',
        translate=True,
        help=(
            'Texto descriptivo que se mostrará debajo del nombre del equipo '
            'en la tarjeta del portal web. Si se deja vacío, se genera '
            'un texto predeterminado automáticamente.'
        ),
    )

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_publish_on_portal(self):
        """Toggle portal publication from backend action."""
        for team in self:
            team.is_published_on_portal = not team.is_published_on_portal
            if team.is_published_on_portal:
                _logger.info(
                    'Helpdesk team "%s" (id=%s) published on portal for company "%s"',
                    team.name, team.id, team.company_id.name,
                )
            else:
                _logger.info(
                    'Helpdesk team "%s" (id=%s) unpublished from portal',
                    team.name, team.id,
                )
