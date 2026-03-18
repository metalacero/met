# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


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

    def write(self, vals):
        old_costs = {}
        if 'standard_price' in vals:
            for variant in self:
                old_costs[variant.id] = variant.standard_price

        result = super().write(vals)

        if 'standard_price' in vals:
            new_cost = vals['standard_price']
            for variant in self:
                old_cost = old_costs.get(variant.id, 0.0)
                if old_cost != new_cost:
                    currency = variant.currency_id.name if variant.currency_id else ''
                    _logger.info(
                        'Costo actualizado para variante %s (ID: %s): %s %s → %s %s',
                        variant.display_name, variant.id,
                        old_cost, currency, new_cost, currency,
                    )
                    variant.product_tmpl_id.message_post(
                        body=(
                            f'<b>Costo actualizado</b> para <i>{variant.display_name}</i>: '
                            f'{old_cost:.4f} {currency} → <b>{new_cost:.4f} {currency}</b>'
                        ),
                        subtype_xmlid='mail.mt_note',
                    )

        return result
