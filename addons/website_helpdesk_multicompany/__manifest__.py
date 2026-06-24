{
    'name': 'Website Helpdesk Multi-Company',
    'version': '18.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Unifica equipos de helpdesk de múltiples compañías en un solo sitio web',
    'description': """
        Permite visualizar y gestionar equipos de helpdesk de todas las compañías
        en un solo portal web. Sobrescribe el controlador de website_helpdesk
        para inyectar equipos de todas las compañías usando sudo(), ignorando
        las reglas de filtrado multi-compañía nativas.
    """,
    'author': 'PROGSUM',
    'website': 'https://www.progsum.com',
    'license': 'OPL-1',
    'depends': [
        'website_helpdesk',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
