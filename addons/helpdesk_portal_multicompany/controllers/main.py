import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk
except ImportError:
    WebsiteHelpdesk = object

class MulticompanyWebsiteHelpdesk(WebsiteHelpdesk):

    @http.route()
    def website_helpdesk(self, team=None, **kwargs):
        # 1. Ejecutar el controlador original para mantener integraciones nativas
        response = super(MulticompanyWebsiteHelpdesk, self).website_helpdesk(team=team, **kwargs)
        
        # 2. Interceptar solo la vista de lista (cuando team no está definido)
        if not team and response and hasattr(response, 'qcontext') and 'teams' in response.qcontext:
            user = request.env.user
            
            # Aplicar solo a usuarios logueados (portal o internos)
            if user.id != request.env.ref('base.public_user').id:
                allowed_companies = user.company_ids.ids
                
                if allowed_companies:
                    # Construir dominio para buscar equipos en todas las compañías permitidas
                    domain = [
                        ('use_website_helpdesk_form', '=', True),
                        ('company_id', 'in', allowed_companies + [False])
                    ]
                    
                    # Respetar la visibilidad de publicación web si no es administrador de helpdesk
                    if not user.has_group('helpdesk.group_helpdesk_manager'):
                        domain.append(('website_published', '=', True))
                        
                    # Buscar con sudo() para evadir cualquier filtro explícito de 'website_id'
                    # o reglas restrictivas del entorno del sitio web actual.
                    teams = request.env['helpdesk.team'].sudo().search(domain, order="sequence, id asc")
                    
                    _logger.info("Controlador Web: Inyectando %s equipos para el usuario %s", len(teams), user.id)
                    
                    # Reemplazar la lista de equipos en el contexto de renderizado de QWeb
                    response.qcontext['teams'] = teams
                    
        return response
