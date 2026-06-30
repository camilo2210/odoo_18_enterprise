import werkzeug
from odoo.exceptions import AccessError

    # ... [Tu método website_helpdesk_teams actual se mantiene intacto arriba] ...

    @http.route([
        '/helpdesk/<int:team>',
        '/helpdesk/<int:team>/submit',
    ], type='http', auth="public", website=True, sitemap=False)
    def website_helpdesk_team(self, team, **kwargs):
        """Override: Intercepta el formulario individual usando <int> en lugar de <model>.
        Esto evita el 404 nativo, nos permite validar la seguridad manualmente
        y corregir el contexto multiempresa.
        """
        # 1. BYPASS DEL 404: Buscamos el equipo ignorando el contexto del website
        team_sudo = request.env['helpdesk.team'].sudo().browse(team)
        
        if not team_sudo.exists():
            raise request.not_found()

        # 2. VALIDACIÓN ESTRICTA DE SEGURIDAD (El 403 manual)
        user = request.env.user
        
        # Si es un usuario portal logueado (no el public_user)
        if user.id != request.env.ref('base.public_user').id:
            # Verificamos si la compañía del equipo está en las compañías permitidas del usuario
            if team_sudo.company_id and team_sudo.company_id.id not in user.company_ids.ids:
                # Lanzamos el Error 403 estándar de Odoo (igual al de tu Imagen 2)
                raise AccessError(
                    "Estos registros están restringidos.\n"
                    f"No tienes acceso a los equipos de soporte de la empresa: {team_sudo.company_id.name}."
                )

        # 3. CORRECCIÓN DE CONTEXTO: Inyectamos la compañía correcta en el entorno.
        # Esto es vital para que al renderizar el formulario (y al enviar el ticket), 
        # Odoo busque los Tipos de Ticket y cree el registro en la Compañía 2, no en la 1.
        team_with_context = team_sudo.with_user(user).with_company(team_sudo.company_id)

        # 4. Delegamos al controlador nativo pasando el registro con el contexto parcheado
        return super().website_helpdesk_team(team=team_with_context, **kwargs)