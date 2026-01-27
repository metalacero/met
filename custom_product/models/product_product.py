# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging
import re

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Related field from product.template for direct access
    is_special = fields.Boolean(
        related='product_tmpl_id.is_special',
        string='Producto Especial',
        readonly=True,
        store=True,
        help='Indica si este producto tiene precios especiales'
    )
    
    price_per_measurement = fields.Float(
        related='product_tmpl_id.price_per_measurement',
        string='Precio por medida',
        readonly=True,
        store=False
    )

    def _get_variant_numeric_value(self):
        """
        Get the numeric value of the variant.
        Searches for a numeric value in the attribute values or display_name.
        If not found, uses the variant index (1, 2, 3, etc.)
        """
        self.ensure_one()
        
        # Search for numeric values in the variant attributes
        if self.product_template_attribute_value_ids:
            for attr_value in self.product_template_attribute_value_ids:
                # Try to extract a number from the attribute value name
                name = attr_value.name or ''
                # Search for numbers in the name (e.g., "1", "2", "3.1'", "Size 3", etc.)
                # Improved regex to capture decimal numbers: matches "3.1" from "3.1'"
                numbers = re.findall(r'\d+\.?\d*', name)
                if numbers:
                    try:
                        numeric_val = float(numbers[0])
                        _logger.info(
                            'Numeric value found in attribute for variant %s (ID: %s): %s (from "%s")',
                            self.display_name, self.id, numeric_val, name
                        )
                        return numeric_val
                    except ValueError:
                        continue
        
        # If not found in attributes, try to extract from display_name
        # Example: "Aluzinc (3.1')" -> extract 3.1
        if self.display_name:
            numbers = re.findall(r'\d+\.?\d*', self.display_name)
            if numbers:
                try:
                    numeric_val = float(numbers[0])
                    _logger.info(
                        'Numeric value found in display_name for variant %s (ID: %s): %s (from "%s")',
                        self.display_name, self.id, numeric_val, self.display_name
                    )
                    return numeric_val
                except ValueError:
                    pass
        
        # If no numeric value is found in attributes or display_name,
        # use the variant index (position in the list of variants sorted by ID)
        variants = self.product_tmpl_id.product_variant_ids.sorted('id')
        try:
            variant_index = list(variants.ids).index(self.id) + 1
            _logger.info(
                'Using variant index for %s (ID: %s): %s',
                self.display_name, self.id, variant_index
            )
            return float(variant_index)
        except (ValueError, IndexError):
            _logger.warning(
                'Could not determine index for variant %s (ID: %s), using 1.0',
                self.display_name, self.id
            )
            return 1.0

    @api.model
    def create(self, vals):
        """Override create to automatically calculate price if special"""
        variant = super(ProductProduct, self).create(vals)
        if variant.is_special and variant.price_per_measurement:
            variant._compute_special_price()
        return variant

    def write(self, vals):
        """Override write to recalculate price when relevant fields change"""
        result = super(ProductProduct, self).write(vals)
        
        # Recalculate if is_special or attributes changed
        # Note: price_per_measurement is related, so it's recalculated from template
        fields_to_check = ['is_special', 'product_template_attribute_value_ids']
        if any(field in vals for field in fields_to_check):
            for variant in self:
                if variant.is_special and variant.price_per_measurement:
                    variant._compute_special_price()
        
        return result

    def _compute_special_price(self):
        """
        Calculate variant price based on numeric value and price_per_measurement
        Price = numeric_value * price_per_measurement
        Updates price_extra of attribute values so lst_price reflects the correct price
        Keeps list_price at 0
        """
        for variant in self:
            if not variant.is_special or not variant.price_per_measurement:
                _logger.debug(
                    'Skipping price calculation for variant %s (ID: %s): is_special=%s, price_per_measurement=%s',
                    variant.display_name, variant.id, variant.is_special, variant.price_per_measurement
                )
                continue
            
            try:
                # Get the unique numeric value for this variant
                numeric_value = variant._get_variant_numeric_value()
                calculated_price = numeric_value * variant.price_per_measurement
                
                # Ensure list_price is at 0
                if variant.list_price != 0.0:
                    variant.sudo().write({'list_price': 0.0})
                
                # Update price_extra in variant attribute values
                # lst_price = list_price + sum(price_extra from attributes), so if list_price=0, lst_price=sum(price_extra)
                # Update price_extra of each attribute value based on its numeric value
                if variant.product_template_attribute_value_ids:
                    attr_values = variant.product_template_attribute_value_ids
                    
                    # First, reset all price_extra to 0 for this variant
                    for attr_value in attr_values:
                        if attr_value.price_extra != 0.0:
                            attr_value.sudo().write({'price_extra': 0.0})
                    
                    # Find the attribute that has the numeric value and update its price_extra
                    found_numeric_attr = False
                    for attr_value in attr_values:
                        name = attr_value.name or ''
                        numbers = re.findall(r'\d+\.?\d*', name)
                        if numbers:
                            try:
                                attr_numeric_value = float(numbers[0])
                                # Calculate price_extra based on the attribute's numeric value
                                attr_price_extra = attr_numeric_value * variant.price_per_measurement
                                
                                # Update this attribute's price_extra
                                attr_value.sudo().write({'price_extra': attr_price_extra})
                                found_numeric_attr = True
                                
                                _logger.info(
                                    'Updated price_extra for variant %s (ID: %s): attribute=%s (value=%s), price_extra=%s',
                                    variant.display_name, variant.id, attr_value.name, attr_numeric_value, attr_price_extra
                                )
                                break
                            except ValueError:
                                continue
                    
                    # If no attribute with numeric value found, use variant index
                    if not found_numeric_attr and len(attr_values) > 0:
                        first_attr_value = attr_values[0]
                        first_attr_value.sudo().write({'price_extra': calculated_price})
                        
                        _logger.info(
                            'Updated price_extra (using variant index) for variant %s (ID: %s): attribute=%s, price_extra=%s',
                            variant.display_name, variant.id, first_attr_value.name, calculated_price
                        )
                
                # Force recomputation of computed fields
                variant.invalidate_recordset(['list_price', 'lst_price', 'price', 'price_extra'])
                variant.refresh()
                
                # Get values after update
                updated_list_price = variant.list_price
                updated_lst_price = variant.lst_price
                updated_price_extra = sum(variant.product_template_attribute_value_ids.mapped('price_extra')) if variant.product_template_attribute_value_ids else 0.0
                
                _logger.info(
                    'Price calculated for variant %s (ID: %s): numeric_value=%s * price_per_measurement=%s = %s | list_price: %s | price_extra_total: %s | lst_price: %s',
                    variant.display_name, variant.id, numeric_value, 
                    variant.price_per_measurement, calculated_price,
                    updated_list_price, updated_price_extra, updated_lst_price
                )
            except Exception as e:
                _logger.error(
                    'Error calculating price for variant %s (ID: %s): %s',
                    variant.display_name, variant.id, str(e), exc_info=True
                )
