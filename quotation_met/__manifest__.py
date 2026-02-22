# -*- coding: utf-8 -*-
{
    'name': 'Quotation Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Validación de inventario antes de confirmar cotizaciones',
    'description': """
        Este módulo valida que exista suficiente inventario antes de confirmar
        una cotización y convertirla en orden de venta.
    """,
    'author': 'Tu Empresa',
    'depends': ['sale', 'stock', 'product', 'account', 'om_account_accountant', 'pos_sale', 'purchase', 'l10n_do_accounting'],
    'data': [
        # 'security/ir_rule.xml',
        'data/payment_methods_data.xml',
        'data/ir_attachment_purchase.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/purchase_order.xml',
        'views/purchase_order_report.xml',
        'views/payment_method_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice.xml',

    ],
    'assets': {
        'point_of_sale.assets': [
            'quotation_met/static/src/js/pos_sale_consolidate.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

