# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    # =========================================================================
    # NEW FIELDS — Portal Multi-Company Configuration
    # =========================================================================

    is_published_on_portal = fields.Boolean(
        string='Publicar en Portal Multicompañía',
        default=False,
        help=(
            'Muestra este equipo en la página centralizada /helpdesk/teams.\n'
            'El formulario de creación de tickets será manejado directamente\n'
            'por el módulo, evitando restricciones de sitio web y errores 404.'
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
        help='Ícono FontAwesome para la tarjeta del equipo en el portal.',
    )

    website_description = fields.Text(
        string='Descripción del Portal',
        translate=True,
        help='Texto para la tarjeta del portal. Vacío = texto automático.',
    )

    # =========================================================================
    # OVERRIDES
    # =========================================================================

    def _compute_website_url(self):
        """Redirige el botón nativo 'Ir al sitio web' a nuestra ruta."""
        super()._compute_website_url()
        for team in self:
            if team.is_published_on_portal:
                team.website_url = '/helpdesk/mc/%d' % team.id
