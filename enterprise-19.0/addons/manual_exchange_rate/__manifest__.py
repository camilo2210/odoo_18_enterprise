# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: ASWIN A K (odoo@cybrosys.com)
#
#    Modifications by Softprimes
#    Copyright (C) 2025-TODAY Softprimes (<http://www.softprimes.com>)
#    Author: Omar Zaki / Softprimes
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': "Manual Exchange Rate",
    'version': '18.0',
    'category': 'Accounting',
    'summary': """By using this module ,we can change the currency rate manually
     in sale ,purchase and invoice. [Update Change Currency in Stock Valuation , add inverse Field For Rate]""",
    'description': """By using this module, we can manually adjust the currency
     rate for key aspects of our business operations, including sales,
     purchases, and invoicing. This feature gives us the power to have precise
     control over currency conversions and adapt quickly to fluctuating 
     exchange rates.""",
    'author': 'Softprimes',
    'website': "http://www.softprimes.com",
    'depends': ['base', 'purchase', 'sale_management', 'account'],
    'data': [
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
    ],
    'images': ['static/description/manual_currency.gif'],
    'license': 'LGPL-3',
    'sequence': -101,
    'installable': True,
    'application': True,
}
