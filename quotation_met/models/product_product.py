# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Fields related from product.template for direct access
    is_restricted_user = fields.Boolean(
        related='product_tmpl_id.is_restricted_user',
        string='Restricted to User',
        readonly=True,
        store=True
    )
    restricted_user_id = fields.Many2one(
        related='product_tmpl_id.restricted_user_id',
        string='Restricted User',
        readonly=True,
        store=True
    )
    price_modifiable = fields.Boolean(
        related='product_tmpl_id.price_modifiable',
        string='Precio Modificable',
        readonly=True,
        store=True
    )

