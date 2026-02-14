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
    price_modifiable = fields.Boolean(
        string='Precio Modificable',
        default=False,
        help='Si está marcado, el precio de este producto puede ser modificado manualmente en órdenes de venta y facturas. Por defecto está activado para productos tipo servicio.'
    )

    @api.model
    def create(self, vals):
        """Auto-marcar price_modifiable para productos tipo servicio"""
        if 'price_modifiable' not in vals and 'detailed_type' in vals:
            if vals.get('detailed_type') == 'service':
                vals['price_modifiable'] = True
        return super().create(vals)

    def write(self, vals):
        """Auto-actualizar price_modifiable cuando cambia el tipo de producto"""
        if 'detailed_type' in vals and vals['detailed_type'] == 'service':
            # Si cambia a servicio y no se especificó price_modifiable, activarlo
            if 'price_modifiable' not in vals:
                vals['price_modifiable'] = True
        return super().write(vals)

