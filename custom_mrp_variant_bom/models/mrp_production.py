# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    variant_id = fields.Many2one(
        'product.product',
        string="Variante del Producto",
        help="Variante específica del producto a fabricar"
    )

    @api.model
    def create(self, vals):
        """Override create to set variant_id from product_id if it's a variant"""
        production = super(MrpProduction, self).create(vals)
        
        # If product_id is a variant of a special product, set variant_id
        if production.product_id and production.product_id.is_special:
            production.variant_id = production.product_id.id
            _logger.info(
                'Manufacturing order %s created for variant %s',
                production.name, production.product_id.display_name
            )
        
        return production
