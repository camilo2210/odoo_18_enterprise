{
    'name': 'Extended Field Creator',
    'summary': 'Create custom fields on any Odoo model via a user-friendly interface — no code required.',
    'description': """
        Extended Field Creator
        ======================
        Allows functional/technical consultants to dynamically create
        new fields on any Odoo model from a simple UI.

        Features:
        - Select target model, field name, type, and help text
        - Auto-generates the technical name with the x_pgm_ prefix
        - Creates the field in the database instantly (no restart needed)
        - Auto-injects the field into the target model's form view
        - Supports: Char, Text, Integer, Float, Boolean, Date, Datetime,
          Html, Binary, Monetary, Many2one, and Selection field types
        - Full audit trail via chatter
        - Clean removal of created fields and their view extensions
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
