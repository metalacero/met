# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Custom MRP Variant BOM',
    'version': '16.0.1.0.0',
    'summary': 'Auto-create BOM for product variants when manufacturing from sales orders',
    'description': '''
        This module automatically creates a BOM (Bill of Materials) for each product variant
        when a sales order is confirmed for special products (is_special=True).
        
        If a BOM already exists for the variant, it uses the existing one.
        This simplifies manufacturing by having a dedicated BOM for each variant with
        the correct component quantities already defined.
    ''',
    'depends': ['base', 'sale', 'mrp', 'sale_management', 'stock', 'custom_product', 'base_setup'],
    'category': 'Manufacturing',
    'data': [
        'data/system_parameters.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
