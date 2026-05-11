{
    "name": "Portal Custom Payment Amount",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Allow customers to enter a custom payment amount from portal invoices",
    "depends": [
        "account",
        "payment",
        "portal",
        "website",
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/portal_invoice_templates.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}