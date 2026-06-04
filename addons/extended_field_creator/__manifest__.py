{
    'name': 'Extended Field Creator',
    'summary': 'Generate custom field code in the extended_fields module via a user-friendly interface.',
    'description': """
        Extended Field Creator — Code Generator
        =========================================
        Allows functional/technical consultants to define new fields
        through a UI and generate the corresponding Python and XML code
        directly into the ``extended_fields`` addon.

        Features:
        - Select target model, field name, type, and help text
        - Auto-generates the technical name with the smm_ prefix
        - Generates Python field definitions in extended_fields/models/
        - Generates XML view extensions in extended_fields/views/
        - Auto-updates __init__.py and __manifest__.py when new files are needed
        - Supports: Char, Text, Integer, Float, Boolean, Date, Datetime,
          Html, Binary, Monetary, Many2one, and Selection field types
        - Full audit trail via chatter
        - Clean removal of generated code (comments out Python, removes XML)
    """,
    'author': 'PROGSUM',
    'website': 'https://www.progsum.com',
    'support': 'info@progsum.com',
    'maintainer': 'PROGSUM',
    'category': 'Technical',
    'version': '18.0.1.0.0',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'extended_fields',
    ],
    'data': [
        'security/extended_field_creator_groups.xml',
        'security/ir.model.access.csv',
        'views/extended_field_creator_views.xml',
        'views/extended_field_creator_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
