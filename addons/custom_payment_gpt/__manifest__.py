{
    'name': 'Portal: Abonos Parciales en Facturas',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Permite a clientes específicos realizar abonos libres desde el portal (Mínimo 1500 COP)',
    'author': 'Odoo GEM / Tu Empresa',
    'depends': [
        'account', 
        'payment', 
        'website_payment',
        'contacts'
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/payment_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_payment_gpt/static/src/js/portal_payment_custom.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}