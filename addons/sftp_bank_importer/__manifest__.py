# -*- coding: utf-8 -*-
{
    'name': 'SFTP Bank Statement Importer',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Bank',
    'summary': 'Import bank statements (CSV) from SFTP via configurable rules',
    'description': """
        Automatically imports bank statement CSV files from a remote SFTP server.
        Supports multiple configurations, keyword file filtering, column mapping,
        duplicate prevention via import logs, and scheduled automation.
    """,
    'author': 'Custom Development',
    'depends': ['account', 'mail'],
    'external_dependencies': {
        'python': ['paramiko'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/sftp_bank_config_views.xml',
        'views/sftp_import_log_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
