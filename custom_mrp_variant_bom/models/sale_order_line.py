# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_procurement_values(self, group_id=False):
        """
        Override to pass variant information to manufacturing orders
        for special products (is_special=True)
        """
        self.ensure_one()
        values = super()._prepare_procurement_values(group_id=group_id)
        
        # For special products (is_special=True), pass variant information
        if self.product_id and self.product_id.is_special:
            values["variant_id"] = self.product_id.id
            
            _logger.info(
                'Preparing procurement values for special product %s: variant_id=%s',
                self.product_id.display_name, self.product_id.id
            )
            
        return values
