{
    'name': 'Website Helpdesk Multi-Company',
    'version': '18.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Publica los equipos de helpdesk de todas las compañías en un solo sitio web',
    'description': """
        Muestra en /helpdesk los equipos de soporte de todas las compañías de la
        base de datos. El acceso a un equipo se restringe a las compañías a las
        que pertenece el usuario (res.users.company_ids); si el equipo es de otra
        compañía se muestra una página de acceso restringido.
    """,
    'author': 'PROGSUM',
    'maintainer': 'PROGSUM',
    'website': 'https://www.progsum.com',
    'license': 'OPL-1',
    'depends': [
        'website_helpdesk',
    ],
    'data': [
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
