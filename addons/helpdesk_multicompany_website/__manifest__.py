# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Multi-Company Website',
    'version': '18.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Página centralizada de equipos de mesa de ayuda multi-compañía en el sitio web',
    'description': """
Helpdesk Multi-Company Website
===============================

Permite configurar y mostrar múltiples equipos de helpdesk de distintas
compañías en una sola página del sitio web, con filtrado automático por
la compañía activa del usuario.

Características principales:
- Página dinámica /helpdesk/teams con todos los equipos publicados
- Filtrado automático por compañía activa del usuario logueado
- Iconos y descripciones configurables por equipo desde el backend
- Escalable: nuevos equipos aparecen automáticamente al publicarlos
- Validación estricta para evitar tickets cross-company
    """,
    'author': 'Custom Development',
    'website': '',
    'depends': [
        'helpdesk',
        'website',
    ],
    'data': [
        'views/helpdesk_team_views.xml',
        'views/website_templates.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
