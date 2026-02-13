# -*- coding: utf-8 -*-
{
    'name': 'Restrict Single Company Selection',
    'version': '18.0.1.0.1',
    'category': 'Tools',
    'summary': 'Restrict users to select only one company at a time',
    'description': """
        This module restricts users from selecting multiple companies simultaneously.
        Only users with specific permission can select multiple companies.
        
        Features:
        - Frontend validation (JavaScript)
        - Backend validation (Python)
        - Configurable per user via security group
        - User-friendly notifications
    """,
    'author': 'Tu Nombre',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/security.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'restrict_single_company/static/src/js/switch_company_menu.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}



