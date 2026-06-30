import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        super()._authenticate(endpoint)
        
        # Verificar que el request exista y tenga atributos HTTP
        if request and hasattr(request, 'httprequest'):
            path = request.httprequest.path
            
            # Interceptar únicamente las rutas relacionadas con el helpdesk público
            if path and path.startswith('/helpdesk'):
                user = request.env.user
                
                # Aplicar lógica exclusivamente para usuarios autenticados (portal o internos).
                # Se excluye al usuario público para mantener el comportamiento estándar de visitantes.
                if user and user.id != request.env.ref('base.public_user').id:
                    allowed_company_ids = user.company_ids.ids
                    if allowed_company_ids:
                        _logger.info("Inyectando contexto multicompañía para el usuario %s en la ruta %s", user.id, path)
                        
                        # Actualizar el entorno global de la petición HTTP inyectando las compañías del usuario.
                        # Esto asegura que el ORM y los conversores de URL (ej. <model("helpdesk.team")>)
                        # evalúen las reglas de registro multicompañía (ir.rule) basándose en los accesos
                        # reales del usuario y no restrictivamente en la compañía del sitio web actual.
                        request.update_env(context=dict(request.env.context, allowed_company_ids=allowed_company_ids))
