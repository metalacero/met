# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_special = fields.Boolean(
        string='Producto Especial',
        default=False,
        help='Indica si este producto tiene precios especiales'
    )

    price_per_measurement = fields.Float(string='Precio por medida')

    @api.model
    def create(self, vals):
        """Override create to calculate variant prices if special"""
        template = super(ProductTemplate, self).create(vals)
        
        # If special and has price_per_measurement, calculate variant prices
        if template.is_special and template.price_per_measurement:
            template.product_variant_ids._compute_special_price()
        
        return template

    def write(self, vals):
        """Override write to recalculate variant prices when price_per_measurement changes"""
        result = super(ProductTemplate, self).write(vals)
        
        # If price_per_measurement or is_special changed, recalculate variant prices
        if 'price_per_measurement' in vals or 'is_special' in vals:
            for template in self:
                if template.is_special and template.price_per_measurement:
                    _logger.info(
                        'Recalculating prices for all variants of template %s (ID: %s). '
                        'Variants found: %s',
                        template.name, template.id, len(template.product_variant_ids)
                    )
                    # Recalculate prices for all variants individually
                    for variant in template.product_variant_ids:
                        variant._compute_special_price()
        
        return result
