# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Multicompany Portal',
    'version': '18.0.1.0.0',
    'summary': 'Portal unificado de equipos de helpdesk para entornos multicompany',
    'description': """
        Permite que un único sitio web principal muestre todos los equipos de helpdesk
        de todas las compañías a las que tiene acceso el usuario portal, manteniendo
        la creación del ticket en la compañía correspondiente al equipo seleccionado.
    """,
    'category': 'Services/Helpdesk',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'helpdesk',
        'helpdesk_website',
        'website',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'helpdesk_multicompany_portal/static/src/css/portal_helpdesk.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}