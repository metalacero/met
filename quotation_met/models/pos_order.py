from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    skip_inventory_moves = fields.Boolean(
        string='No afectar inventario',
        default=False,
        help='Si está activado, las ventas del POS no afectarán el inventario ni crearán órdenes de salida'
    )



class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def _should_create_picking_real_time(self):
        """
        Sobrescribimos para evitar crear pickings en tiempo real si skip_inventory_moves está activado
        """
        # Forzar lectura del campo desde la base de datos
        config = self.config_id.sudo()
        skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
        
        if skip_inventory:
            _logger.info('skip_inventory_moves está activado para POS %s (ID: %s). No se creará picking en tiempo real.', 
                        config.name, config.id)
            return False
        return super(PosOrder, self)._should_create_picking_real_time()
    
    def _create_order_picking(self):
        """
        # We override the method that creates pickings (delivery orders).
        # If the POS is configured to not affect inventory, we do NOTHING related to inventory:
        # - We do not update demand quantities on stock moves
        # - We do not cancel pickings
        # - We do not create pickings
        #
        # We also block operations if related pickings are already in 'done' state (already dispatched)
        # because the POS should only process payments, not affect already processed inventory.
        """
        # Force reading the field from the database
        config = self.config_id.sudo()
        skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
        
        if skip_inventory:
            _logger.info(
                'skip_inventory_moves está activado para orden POS %s (ID: %s). '
                'No se realizará ninguna operación de inventario (no se actualizarán demandas, no se cancelarán pickings, no se crearán pickings).', 
                self.name, self.id
            )
            # Return False to avoid executing any inventory logic
            # This avoids executing the base code that updates demand quantities and cancels pickings
            return False
        
        # Verify if there are related pickings that are already in 'done' state
        # If so, save the original quantities and restore them after
        so_lines = self.lines.mapped('sale_order_line_id')
        moves_to_restore = {}  # {move_id: original_qty}
        if so_lines:
            # Save the original quantities BEFORE executing the code
            for so_line in so_lines:
                if so_line.move_ids:
                    for move in so_line.move_ids:
                        if move.picking_id and move.picking_id.state == 'done':
                            moves_to_restore[move.id] = move.product_uom_qty
                            _logger.info(
                                'Guardando cantidad original para movimiento %s (picking %s): %s',
                                move.name, move.picking_id.name, move.product_uom_qty
                            )
        
        # Execute the base code (which can update the quantities to 0)
        result = super(PosOrder, self)._create_order_picking()
        
        # Restore the original quantities if they were changed to 0
        if moves_to_restore:
            for move_id, original_qty in moves_to_restore.items():
                move = self.env['stock.move'].browse(move_id)
                if move.exists() and move.picking_id and move.picking_id.state == 'done':
                    # If the quantity was changed to 0, restore the original
                    if move.product_uom_qty == 0 and original_qty > 0:
                        # Use write() to avoid our own blocking interfering
                        move.sudo().write({'product_uom_qty': original_qty})
                        _logger.info(
                            'Cantidad restaurada para movimiento %s (picking %s): %s (era 0, restaurado a %s)',
                            move.name, move.picking_id.name, original_qty, original_qty
                        )
        
        # Normal behavior if the option is not activated and there are no pickings in 'done' state
        return super(PosOrder, self)._create_order_picking()