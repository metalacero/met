# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Custom Sales Order Lines",
    "version": "16.0.1.3.0",
    "summary": "Extend sales order lines to include custom attributes for special products",
    "depends": ["base", "sale", "mrp", "sale_management"],
    "category": "Sales",
    "data": [
        "views/product_views.xml",
        "views/sale_order_line_views.xml",
        "views/account_move_line_views.xml",
        "views/mrp_production_view.xml",
        "views/report_templates.xml",
    ],
    "installable": True,
}
