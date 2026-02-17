from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _get_product_domain(self):
        """Filtrar productos restringidos en las líneas de venta"""
        # DESACTIVADO: Restricción de productos por usuario deshabilitada
        domain = []
        # user = self.env.user
        
        # # if user is not admin, filter restricted products
        # if not user.has_group('base.group_system'):
        #     domain = [
        #         '|',
        #         ('is_restricted_user', '=', False),
        #         '|',
        #         ('restricted_user_id', '=', False),
        #         ('restricted_user_id', '=', user.id)
        #     ]
        
        return domain

    def read_converted(self):
        """
        # Override to allow the POS to display the correct quantities
        # when fetching orders that have already been delivered (pickings in 'done').
        #
        # When the picking is in 'done', qty_delivered = product_uom_qty,
        # so qty_to_invoice = 0. But the POS needs to display the original
        # quantity (product_uom_qty) so it can invoice the correct amount.
        """
        _logger.info('read_converted called for %s sale lines', len(self))
        
        # Call the base method
        results = super(SaleOrderLine, self).read_converted()
        
        _logger.info('read_converted base returned %s results', len(results))
        
        # Check if there are pickings in 'done' for these lines
        for sale_line in self:
            if sale_line.move_ids:
                pickings = sale_line.move_ids.mapped('picking_id')
                done_pickings = pickings.filtered(lambda p: p.state == 'done')
                
                if done_pickings:
                    # If there are pickings in 'done', find the corresponding result
                    # The result may have the id directly or in a different format
                    for idx, result in enumerate(results):
                        # Check if this result corresponds to this sale line
                        result_id = result.get('id')
                        if result_id == sale_line.id or (isinstance(result_id, list) and sale_line.id in result_id):
                            # When the picking is in 'done', qty_to_invoice may be 0
                            # but we need to show the original quantity so the POS can charge
                            current_qty_to_invoice = result.get('qty_to_invoice', 0)
                            current_product_uom_qty = result.get('product_uom_qty', 0)
                            
                            _logger.info(
                                'Línea de venta %s (ID: %s) tiene picking en "done". '
                                'Valores actuales: qty_to_invoice=%s, product_uom_qty=%s, '
                                'qty_delivered=%s, qty_invoiced=%s, product_uom_qty (campo)=%s',
                                sale_line.display_name, sale_line.id, current_qty_to_invoice, current_product_uom_qty,
                                sale_line.qty_delivered, sale_line.qty_invoiced, sale_line.product_uom_qty
                            )
                            
                            # When the picking is in 'done', ALWAYS use product_uom_qty as the available quantity
                            # to charge, regardless of qty_to_invoice, because the POS should only charge
                            # and the inventory has already been processed
                            if sale_line.product_uom_qty > 0:
                                # Use product_uom_qty as the available quantity to charge
                                original_qty = sale_line.product_uom_qty
                                
                                # Convert the quantity if necessary using the pos_sale method
                                # The _convert_qty method is in the pos_sale module and is @api.model
                                if sale_line.product_id.uom_id != sale_line.product_uom:
                                    # Use the _convert_qty method of the model (inherited from pos_sale)
                                    if hasattr(self, '_convert_qty'):
                                        original_qty = self._convert_qty(sale_line, original_qty, 's2p')
                                    else:
                                        # If not available, convert manually
                                        original_qty = sale_line.product_uom._compute_quantity(
                                            original_qty, sale_line.product_id.uom_id, False
                                        )
                                
                                # ALWAYS update qty_to_invoice and product_uom_qty when there are pickings in 'done'
                                # to ensure the POS displays the correct quantity
                                # IMPORTANT: Also adjust qty_delivered to 0 for the JavaScript calculation to work:
                                # quantity = product_uom_qty - Math.max(qty_delivered, qty_invoiced)
                                # If qty_delivered = product_uom_qty, then quantity = 0
                                # So we put qty_delivered = 0 when the picking is in 'done'
                                result['qty_to_invoice'] = original_qty
                                result['product_uom_qty'] = original_qty
                                result['qty_delivered'] = 0  # Adjust to 0 for the JavaScript calculation to work
                                _logger.info(
                                    'Picking in "done" detected. Adjusting qty_to_invoice from %s to %s, product_uom_qty to %s, and qty_delivered to 0 to allow POS charging.',
                                    current_qty_to_invoice, original_qty, original_qty
                                )
                            break
        
        return results
