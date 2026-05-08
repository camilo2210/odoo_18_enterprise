# -*- coding: utf-8 -*-
{
    'name': 'Payment Link - Custom Amount',
    'version': '18.0.1.0.0',
    'summary': 'Permite pagos parciales y montos personalizados en payment links',
    'description': """
        Extiende el portal de pago de Odoo para permitir a los clientes:
        - Pagar el total de la factura
        - Pagar un monto parcial (si está configurado)
        - Ingresar un monto personalizado inferior al total
        Compatible con Mercado Pago y Stripe.
        El monto mínimo respeta el estándar de Mercado Pago Colombia (COP 1,500).
    """,
    'category': 'Accounting/Accounting',
    'author': 'Custom Development',
    'depends': [
        'account',
        'payment',
        'portal',
        'account_payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/payment_custom_amount_groups.xml',
        'views/res_partner_views.xml',
        'views/payment_link_wizard_views.xml',
        'views/payment_portal_templates.xml',
        'data/payment_custom_amount_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_custom_amount/static/src/css/payment_custom_amount.css',
            'payment_custom_amount/static/src/js/payment_custom_amount.js',
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