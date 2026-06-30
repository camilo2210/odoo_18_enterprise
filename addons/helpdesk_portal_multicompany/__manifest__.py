{
    'name': 'Helpdesk Portal Multicompany',
    'version': '18.0.1.0.0',
    'category': 'Website/Helpdesk',
    'summary': 'Visualización y creación de tickets multicompañía desde un único portal',
    'description': """
        Este módulo adapta el comportamiento del sitio web para equipos de soporte.
        Permite que un usuario portal autenticado visualice todos los equipos de las compañías
        a las que tiene acceso, sin importar en qué sitio web (y su compañía asociada) se encuentre.
        Garantiza que, al crear el ticket, este se asigne estrictamente a la compañía del equipo.
    """,
    'author': 'Celaris',
    'depends': ['website_helpdesk', 'helpdesk'],
    'data': [],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
