# -*- coding: utf-8 -*-
{
    'name': 'Payment Link - Custom Amount',
    'version': '18.0.2.0.0',
    'summary': 'Permite pagos con monto personalizado en payment links',
    'category': 'Accounting/Accounting',
    'author': 'Custom Development',
    'depends': [
        'account',
        'payment',
        'portal',
        'account_payment',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/payment_custom_amount_groups.xml',
        'data/payment_custom_amount_data.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/payment_link_wizard_views.xml',
        'views/payment_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_custom_amount/static/src/js/payment_custom_amount.js',
            'payment_custom_amount/static/src/css/payment_custom_amount.css',
            'payment_custom_amount/static/src/js/payment_custom_amount_ui.js',
        ],
        'web.assets_backend': [
            'payment_custom_amount/static/src/css/payment_custom_amount_backend.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}