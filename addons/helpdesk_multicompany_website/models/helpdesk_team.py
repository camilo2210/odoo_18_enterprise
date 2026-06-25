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

    # Remove check_company so admins can assign any website to any team.
    # In multi-company setups, websites don't always map 1:1 to companies.
    website_id = fields.Many2one(check_company=False)

    # -------------------------------------------------------------------------
    # NEW FIELDS — Portal Multi-Company Configuration
    # -------------------------------------------------------------------------

    is_published_on_portal = fields.Boolean(
        string='Publicar en Portal Multicompañía',
        default=False,
        help=(
            'Si está activo, este equipo se mostrará en la página centralizada '
            'de equipos de mesa de ayuda (/helpdesk/teams) y su formulario de '
            'tickets será accesible desde CUALQUIER sitio web del entorno, '
            'independientemente del sitio web que tenga asignado el equipo.\n\n'
            'Esto evita errores 404 cuando hay varios sitios web (uno por '
            'compañía) pero un solo dominio sin subdominios.'
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
        help=(
            'Texto para la tarjeta del portal. '
            'Si se deja vacío, se genera texto automático.'
        ),
    )

    # -------------------------------------------------------------------------
    # KEY OVERRIDE: bypass website restriction for portal-published teams
    # -------------------------------------------------------------------------

    def can_access_from_current_website(self, website_id=False):
        """Allow portal-published teams to be accessed from ANY website.

        Odoo calls this method from the model converter in ir.http during URL
        routing. If it returns False for a record, Odoo raises a 404 NotFound.

        Default behavior (from website.multi.mixin):
            return not self.website_id or self.website_id == current_website

        Our override:
            - If is_published_on_portal is True → always return True (no 404)
            - Otherwise → use the default Odoo behavior
        """
        # self is a recordset; check each record individually
        for team in self:
            if team.is_published_on_portal:
                # This team must be accessible from any website
                continue
            # For non-portal teams, use the native check
            try:
                accessible = super(HelpdeskTeam, team).can_access_from_current_website(
                    website_id
                )
                if not accessible:
                    return False
            except Exception:
                # If parent doesn't have this method, allow access
                pass
        return True

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains('is_published_on_portal', 'website_id')
    def _check_portal_and_website_published(self):
        """Ensure portal-published teams are also published on website.

        A team's /helpdesk/<slug> page returns 404 if the team is not
        published (is_published=False). We warn about this so admins know.
        """
        for team in self:
            if not team.is_published_on_portal:
                continue
            # Check if team is published on website (field name varies by version)
            is_web_published = (
                getattr(team, 'is_published', None)
                or getattr(team, 'website_published', None)
            )
            if is_web_published is False:
                raise ValidationError(_(
                    'El equipo "%(team)s" está configurado para el Portal '
                    'Multicompañía pero NO está publicado en el sitio web.\n\n'
                    'Su URL /helpdesk/... retornará 404 para usuarios '
                    'no administradores.\n\n'
                    'Active "Publicado" en la sección de sitio web del equipo '
                    'o use el botón "Ir al sitio web" → "Publicar".',
                    team=team.name,
                ))

    # -------------------------------------------------------------------------
    # ONCHANGE — UX helpers in the form
    # -------------------------------------------------------------------------

    @api.onchange('is_published_on_portal')
    def _onchange_is_published_on_portal(self):
        """Auto-publish on website when enabling portal publication."""
        if not self.is_published_on_portal:
            return
        changed = []
        if 'is_published' in self._fields and not self.is_published:
            self.is_published = True
            changed.append('Publicado en el sitio web')
        elif 'website_published' in self._fields and not self.website_published:
            self.website_published = True
            changed.append('Publicado en el sitio web')
        if changed:
            return {
                'warning': {
                    'title': _('Ajustes automáticos aplicados'),
                    'message': _(
                        'Para evitar errores 404, se han aplicado los '
                        'siguientes cambios automáticamente:\n- %s\n\n'
                        'Nota: El equipo seguirá teniendo su sitio web '
                        'asignado pero será accesible desde CUALQUIER '
                        'dominio gracias al módulo Portal Multicompañía.',
                        '\n- '.join(changed),
                    ),
                }
            }

    # -------------------------------------------------------------------------
    # CRUD — auto-publish on create/write
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_published_on_portal'):
                if 'is_published' not in vals:
                    vals['is_published'] = True
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('is_published_on_portal'):
            vals = dict(vals)
            if 'is_published' not in vals and 'website_published' not in vals:
                if 'is_published' in self._fields:
                    vals['is_published'] = True
                elif 'website_published' in self._fields:
                    vals['website_published'] = True
            _logger.info(
                'Portal publication enabled for teams %s: auto-published.',
                self.mapped('name'),
            )
        return super().write(vals)

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def action_publish_on_portal(self):
        """Toggle portal publication from backend button."""
        for team in self:
            team.is_published_on_portal = not team.is_published_on_portal
            _logger.info(
                'Helpdesk team "%s" (id=%s) portal portal=%s company="%s"',
                team.name, team.id,
                team.is_published_on_portal,
                team.company_id.name,
            )
