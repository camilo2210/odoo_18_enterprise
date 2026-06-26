# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Multi-Company Website',
    'version': '18.0.3.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Página centralizada de mesa de ayuda para entornos multi-compañía',
    'description': """
Helpdesk Multi-Company Website
===============================

Muestra múltiples equipos de helpdesk de distintas compañías en una
sola página del sitio web, sin necesitar subdominios.

Arquitectura de seguridad (sin sudo() en controladores):
- ACL (ir.model.access.csv): define qué grupos pueden leer qué modelos
- Record rules: restringen qué registros son visibles por grupo
- Método de servicio en el modelo: único punto de elevación de privilegio
  documentado y acotado (solo para res.partner en flujo de portal)

Rutas del módulo:
- /helpdesk/teams         : selector de equipos por compañía
- /helpdesk/mc/<team_id>  : formulario de ticket (sin restricción website_id)
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'helpdesk',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/helpdesk_mc_security.xml',
        'views/helpdesk_team_views.xml',
        'views/website_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
