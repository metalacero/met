# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_restricted_user = fields.Boolean(
        string='Restricted to User',
        help='If checked, this product will only be visible to the selected user'
    )
    restricted_user_id = fields.Many2one(
        'res.users',
        string='Restricted User',
        help='User who can see this product when restriction is active'
    )

