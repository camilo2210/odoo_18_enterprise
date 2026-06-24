# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    # -------------------------------------------------------------------------
    # FIELD OVERRIDES
    # -------------------------------------------------------------------------

    # Override website_id: remove check_company so admins CAN assign a website
    # from a different company to a team. This is necessary in multi-company
    # environments where websites don't map 1:1 to companies.
    website_id = fields.Many2one(check_company=False)

    # -------------------------------------------------------------------------
    # NEW FIELDS — Portal Multi-Company Configuration
    # -------------------------------------------------------------------------

    is_published_on_portal = fields.Boolean(
        string='Publicar en Portal Multicompañía',
        default=False,
        help=(
            'Si está activo, este equipo se mostrará en la página centralizada '
            'de equipos de mesa de ayuda del sitio web (/helpdesk/teams).\n\n'
            'IMPORTANTE: Al activar esta opción, se eliminará automáticamente '
            'la restricción de sitio web (campo "Sitio Web") para que el '
            'formulario de tickets de este equipo sea accesible desde '
            'CUALQUIER sitio web del entorno, evitando errores 404.'
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
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('is_published_on_portal', 'website_id')
    def _check_portal_no_website_restriction(self):
        """Portal-published teams MUST NOT have a website restriction.

        If a team has website_id set, its helpdesk form (/helpdesk/<slug>)
        is only accessible on THAT specific website. When users browse
        the multi-company portal page from a different website and click
        "Crear Ticket", they would get a 404 error.

        Forcing website_id=False makes the form accessible on ALL websites.
        """
        for team in self:
            if team.is_published_on_portal and team.website_id:
                raise ValidationError(_(
                    'El equipo "%(team)s" está publicado en el Portal '
                    'Multicompañía y no puede tener restricción de sitio web.\n\n'
                    'Vacíe el campo "Sitio Web" del equipo para que su '
                    'formulario de tickets sea accesible desde cualquier '
                    'sitio web y evitar errores 404.\n\n'
                    'Esto sucede automáticamente al activar el toggle — '
                    'si ve este error, vacíe manualmente el campo "Sitio Web".',
                    team=team.name,
                ))

    # -------------------------------------------------------------------------
    # ONCHANGE — UX: auto-clear website_id in UI
    # -------------------------------------------------------------------------

    @api.onchange('is_published_on_portal')
    def _onchange_is_published_on_portal(self):
        """Auto-clear website restriction when publishing on portal.

        This provides a smooth admin experience: the user enables the
        toggle and the website restriction is cleared automatically with
        a warning explaining why.
        """
        if self.is_published_on_portal and self.website_id:
            self.website_id = False
            return {
                'warning': {
                    'title': _('Restricción de sitio web eliminada'),
                    'message': _(
                        'Se ha eliminado la restricción de sitio web de este '
                        'equipo para que su formulario de creación de tickets '
                        'sea accesible desde CUALQUIER sitio web.\n\n'
                        'Esto evita errores 404 cuando un usuario accede al '
                        'formulario desde un sitio web diferente al configurado '
                        'originalmente en el equipo.'
                    ),
                }
            }

    # -------------------------------------------------------------------------
    # CRUD OVERRIDES — enforce website_id=False for portal teams
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Force website_id=False for portal-published teams on creation."""
        for vals in vals_list:
            if vals.get('is_published_on_portal'):
                vals['website_id'] = False
                _logger.info(
                    'Creating portal-published team "%s": website_id forced '
                    'to False for cross-website accessibility.',
                    vals.get('name', _('Nuevo')),
                )
        return super().create(vals_list)

    def write(self, vals):
        """Enforce website_id=False when enabling portal publication.

        Also prevents setting website_id on teams that are already
        portal-published.
        """
        # Case 1: Enabling portal publication → force clear website_id
        if vals.get('is_published_on_portal'):
            vals = dict(vals)  # Don't mutate the original
            vals['website_id'] = False
            _logger.info(
                'Portal publication enabled for teams %s: '
                'website_id forced to False.',
                self.mapped('name'),
            )

        # Case 2: Setting website_id on already portal-published teams
        elif 'website_id' in vals and vals.get('website_id'):
            portal_teams = self.filtered('is_published_on_portal')
            if portal_teams:
                _logger.warning(
                    'Blocked website_id assignment on portal-published '
                    'teams: %s. Portal teams must have website_id=False.',
                    portal_teams.mapped('name'),
                )
                # Write other vals to portal teams (without website_id)
                other_vals = {k: v for k, v in vals.items() if k != 'website_id'}
                if other_vals:
                    super(HelpdeskTeam, portal_teams).write(other_vals)
                # Write full vals to non-portal teams
                non_portal = self - portal_teams
                if non_portal:
                    return super(HelpdeskTeam, non_portal).write(vals)
                return True

        return super().write(vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_publish_on_portal(self):
        """Toggle portal publication from backend button."""
        for team in self:
            team.is_published_on_portal = not team.is_published_on_portal
            if team.is_published_on_portal:
                _logger.info(
                    'Helpdesk team "%s" (id=%s) published on portal '
                    'for company "%s"',
                    team.name, team.id, team.company_id.name,
                )
            else:
                _logger.info(
                    'Helpdesk team "%s" (id=%s) unpublished from portal',
                    team.name, team.id,
                )
