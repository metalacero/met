# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        """
        Override to find or create BOM for variant
        """
        mo_vals = super(StockRule, self)._prepare_mo_vals(
            product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom
        )
        
        _logger.info(
            'StockRule._prepare_mo_vals: product=%s (ID: %s), values keys=%s, bom=%s',
            product_id.display_name,
            product_id.id,
            list(values.keys()) if values and isinstance(values, dict) else 'N/A',
            bom.display_name if bom else 'None'
        )
        
        # Get variant_id - product_id is already the variant!
        variant_id = None
        
        # First check if product_id itself is a special variant
        if product_id and product_id.is_special:
            variant_id = product_id.id
            _logger.info('StockRule: product_id %s is a special variant, using it as variant_id: %s', 
                        product_id.display_name, variant_id)
        
        # Also try to get from procurement values (may be filtered out)
        if values and isinstance(values, dict):
            variant_id_from_values = values.get('variant_id')
            if variant_id_from_values:
                _logger.info('StockRule: variant_id from values: %s', variant_id_from_values)
                variant_id = variant_id_from_values
            
            # Try to get from sale_line_id (values may be filtered)
            if values.get('sale_line_id'):
                sale_line = self.env['sale.order.line'].browse(values['sale_line_id'])
                if sale_line.exists():
                    _logger.info(
                        'StockRule: Checking sale_line_id %s, product=%s (ID: %s), is_special=%s',
                        sale_line.id,
                        sale_line.product_id.display_name if sale_line.product_id else 'None',
                        sale_line.product_id.id if sale_line.product_id else None,
                        sale_line.product_id.is_special if sale_line.product_id else False
                    )
                    if sale_line.product_id and sale_line.product_id.is_special:
                        variant_id = sale_line.product_id.id
                        _logger.info('StockRule: variant_id from sale_line: %s', variant_id)
                    else:
                        _logger.info('StockRule: Product from sale_line is not special')
                else:
                    _logger.warning('StockRule: sale_line_id %s does not exist', values.get('sale_line_id'))
            else:
                _logger.info('StockRule: No sale_line_id in values')
        
        # If we have a variant, find or create BOM for it
        if variant_id:
            variant = self.env['product.product'].browse(variant_id)
            if variant.exists():
                _logger.info(
                    'StockRule: Processing variant %s (ID: %s), is_special=%s',
                    variant.display_name, variant.id, variant.is_special
                )
                
                if variant.is_special:
                    # Find existing BOM for this variant
                    variant_bom = self.env['mrp.bom'].search([
                        ('product_id', '=', variant_id),
                        ('company_id', '=', company_id.id if company_id else False)
                    ], limit=1)
                    
                    if variant_bom:
                        _logger.info(
                            'Found existing BOM %s (ID: %s) for variant %s',
                            variant_bom.display_name, variant_bom.id, variant.display_name
                        )
                        mo_vals['bom_id'] = variant_bom.id
                    else:
                        # Create new BOM for this variant with configured component
                        _logger.info(
                            'No BOM found for variant %s (ID: %s). Creating new BOM. Company ID: %s',
                            variant.display_name, variant.id, company_id.id if company_id else False
                        )
                        variant_bom = self._create_variant_bom(variant, company_id)
                        if variant_bom:
                            mo_vals['bom_id'] = variant_bom.id
                            _logger.info(
                                'SUCCESS: Created new BOM %s (ID: %s) for variant %s and assigned to mo_vals',
                                variant_bom.display_name, variant_bom.id, variant.display_name
                            )
                        else:
                            _logger.error('ERROR: Failed to create BOM for variant %s. Check error logs above.', variant.display_name)
                else:
                    _logger.info('Variant %s is not special, skipping BOM creation', variant.display_name)
            else:
                _logger.warning('Variant with ID %s does not exist', variant_id)
        else:
            _logger.info('No variant_id found, using default BOM')
        
        return mo_vals

    def _create_variant_bom(self, variant, company_id):
        """
        Create a new BOM for a variant with product bobina as component
        """
        try:
            _logger.info('_create_variant_bom called for variant %s (ID: %s)', variant.display_name, variant.id)
            
            # Get variant numeric value (e.g., 3.1 from "Aluzinc (3.1')")
            variant_numeric_value = variant._get_variant_numeric_value()
            _logger.info('Variant numeric value: %s', variant_numeric_value)
            
            # Get product bobina - search by default_code from system parameter
            bobina_code = self.env['ir.config_parameter'].sudo().get_param(
                'custom_mrp_variant_bom.bobina_product_code', 
                'BAN01'  # Default fallback
            )
            bobina_product = self.env['product.product'].search([
                ('default_code', '=', bobina_code)
            ], limit=1)
            
            # If not found, try to find by name containing "BOBINA"
            if not bobina_product:
                bobina_product = self.env['product.product'].search([
                    ('name', 'ilike', 'BOBINA ALUZINC')
                ], limit=1)
            
            if not bobina_product:
                _logger.error('ERROR: Product bobina (%s or BOBINA ALUZINC) does not exist', bobina_code)
                # Log all products with BOBINA in name for debugging
                all_bobinas = self.env['product.product'].search([('name', 'ilike', 'BOBINA')])
                _logger.error('Found products with BOBINA in name: %s', 
                             [(p.id, p.default_code, p.name) for p in all_bobinas[:10]])
                return False
            
            _logger.info('Found bobina product: %s (ID: %s, Code: %s)', 
                        bobina_product.display_name, bobina_product.id, bobina_product.default_code)
            
            # Get UOM for bobina (usually pie/feet)
            bobina_uom = bobina_product.uom_id
            _logger.info('Bobina UOM: %s (ID: %s)', bobina_uom.name, bobina_uom.id)
            
            # Create BOM line with bobina
            bom_lines = [(0, 0, {
                'product_id': bobina_product.id,
                'product_qty': variant_numeric_value,  # Quantity = variant numeric value (e.g., 3.1 pies)
                'product_uom_id': bobina_uom.id,
            })]
            
            _logger.info('Prepared BOM line: product_id=%s, qty=%s, uom_id=%s', 
                        bobina_product.id, variant_numeric_value, bobina_uom.id)
            
            # Get product UOM (usually Plancha)
            product_uom = variant.uom_id
            _logger.info('Variant UOM: %s (ID: %s)', product_uom.name, product_uom.id)
            
            # Create the variant BOM
            bom_vals = {
                'product_id': variant.id,
                'product_tmpl_id': variant.product_tmpl_id.id,
                'product_qty': 1.0,  # 1 unit of the variant
                'product_uom_id': product_uom.id,
                'type': 'normal',
                'company_id': company_id.id if company_id else False,
                'bom_line_ids': bom_lines,
            }
            
            _logger.info('Creating BOM with values: %s', bom_vals)
            
            variant_bom = self.env['mrp.bom'].create(bom_vals)
            
            _logger.info(
                'Created BOM for variant %s with bobina (ID: 941). Quantity: %s %s',
                variant.display_name, variant_numeric_value, bobina_uom.name
            )
            
            return variant_bom
            
        except Exception as e:
            _logger.error(
                'ERROR: Exception creating BOM for variant %s: %s',
                variant.display_name, str(e)
            )
            import traceback
            _logger.error(traceback.format_exc())
            return False
