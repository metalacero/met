# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom Product Special Prices',
    'version': '16.0.1.0.0',
    'summary': 'Extend product capabilities to include special prices',
    'depends': ['product'],
    'category': 'Sales',
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
