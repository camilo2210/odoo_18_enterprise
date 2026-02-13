# -*- coding: utf-8 -*-
{
    'name': 'Accounting Second Currency Exchange',
    'description': """
        Account Automatic Transfers
        ===========================
        Manage automatic Currency between Multi Currencies.
    """,
    'version': '18.0',
    'author': "Bn Technologies",
    'category': 'Accounting/Accounting',
    'depends': ['base', 'account', 'sale'],
    'data': [
        'views/account_views_inherit.xml',
        'views/res_company_inherit.xml',
        'views/res_settings_inherit.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
}
