# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


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


    list_price = fields.Float(
        string = "Precio de Venta",
        tracking=True
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
            if 'price_modifiable' not in vals:
                vals['price_modifiable'] = True

        # Capturar valores anteriores antes del write
        old_vals = {}
        if 'name' in vals or ('standard_price' in vals and any(len(t.product_variant_ids) == 1 for t in self)):
            for template in self:
                old_vals[template.id] = {
                    'name': template.name,
                    'standard_price': template.standard_price if len(template.product_variant_ids) == 1 else None,
                }

        result = super().write(vals)

        for template in self:
            old = old_vals.get(template.id, {})
            messages = []

            if 'name' in vals and old.get('name') != vals['name']:
                _logger.info(
                    'Nombre actualizado para producto (ID: %s): "%s" → "%s"',
                    template.id, old.get('name'), vals['name'],
                )
                messages.append(
                    f'<b>Nombre actualizado</b>: {old.get("name")} → <b>{vals["name"]}</b>'
                )

            if 'standard_price' in vals and old.get('standard_price') is not None:
                old_cost = old['standard_price']
                new_cost = vals['standard_price']
                if old_cost != new_cost:
                    currency = template.currency_id.name if template.currency_id else ''
                    _logger.info(
                        'Costo actualizado para producto %s (ID: %s): %s %s → %s %s',
                        template.name, template.id,
                        old_cost, currency, new_cost, currency,
                    )
                    messages.append(
                        f'<b>Costo actualizado</b>: {old_cost:.4f} {currency} → <b>{new_cost:.4f} {currency}</b>'
                    )

            if messages:
                template.message_post(
                    body='<br/>'.join(messages),
                    subtype_xmlid='mail.mt_note',
                )

        return result
