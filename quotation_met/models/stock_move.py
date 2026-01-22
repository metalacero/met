# -*- coding: utf-8 -*-

from odoo import models, api, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_related_pos_orders(self, move):
        """Get all POS orders related to a move"""
        pos_orders = self.env['pos.order']
        
        if not move.picking_id:
            return pos_orders
        
        picking = move.picking_id
        
        # Check if the picking is related to a sale order that has POS invoices
        if picking.sale_id:
            invoices = picking.sale_id.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
            )
            
            for invoice in invoices:
                pos_order = self.env['pos.order'].sudo().search([
                    ('account_move', '=', invoice.id)
                ], limit=1)
                
                if pos_order:
                    pos_orders |= pos_order
        
        # Check if there are POS invoices related to this picking
        if picking.move_ids and move.product_id:
            # Search for invoices that contain this product and are related to POS
            invoice_lines = self.env['account.move.line'].sudo().search([
                ('product_id', '=', move.product_id.id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted')
            ])
            
            for inv_line in invoice_lines:
                invoice = inv_line.move_id
                pos_order = self.env['pos.order'].sudo().search([
                    ('account_move', '=', invoice.id)
                ], limit=1)
                
                if pos_order:
                    # Verificar relación
                    is_related = False
                    if picking.partner_id and invoice.partner_id:
                        is_related = (picking.partner_id == invoice.partner_id)
                    
                    if not is_related and picking.scheduled_date and invoice.invoice_date:
                        date_diff = abs((picking.scheduled_date.date() - invoice.invoice_date).days)
                        is_related = (date_diff <= 1)
                    
                    if is_related:
                        pos_orders |= pos_order
            
            # Check if there are POS orders with payments applied
            if picking.partner_id:
                date_limit = datetime.now() - timedelta(days=1)
                
                found_pos_orders = self.env['pos.order'].sudo().search([
                    ('state', 'in', ['paid', 'done', 'invoiced']),
                    ('partner_id', '=', picking.partner_id.id),
                    ('date_order', '>=', date_limit),
                    ('payment_ids', '!=', False),
                    ('lines.product_id', '=', move.product_id.id)
                ])
                
                for pos_order in found_pos_orders:
                    pos_date = pos_order.date_order.date() if pos_order.date_order else None
                    picking_date = picking.scheduled_date.date() if picking.scheduled_date else None
                    
                    date_match = False
                    if pos_date and picking_date:
                        date_diff = abs((picking_date - pos_date).days)
                        date_match = (date_diff <= 1)
                    
                    if date_match or not picking_date:
                        pos_orders |= pos_order
        
        return pos_orders
    
    def _is_related_to_pos(self, move):
        """Check if a move is related to POS"""
        pos_orders = self._get_related_pos_orders(move)
        return bool(pos_orders)

    def _action_assign(self, force_qty=None):
        """Override _action_assign to prevent demand update when it is related to POS.
        The POS should only create invoices and apply payments, without affecting inventory.
        NOTE: We only block if the picking comes DIRECTLY from a POS order, not if it comes from a regular sale order."""
        moves_to_assign = self.env['stock.move']
        
        for move in self:
            if move.state in ('assigned', 'done', 'cancel'):
                moves_to_assign |= move
                continue
            
            # Block if the picking comes DIRECTLY from a POS order, not from a regular sale order
            # If the picking has sale_id, it means it comes from a regular sale order, not from a POS order directly
            if move.picking_id and move.picking_id.sale_id:
                # Comes from a regular sale order, allow processing normally
                moves_to_assign |= move
                continue
            
            pos_orders = self._get_related_pos_orders(move)
            if pos_orders:
                # Check if any of the related POS orders have skip_inventory_moves activated
                should_block = False
                for pos_order in pos_orders:
                    config = pos_order.config_id.sudo()
                    skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
                    if skip_inventory:
                        should_block = True
                        _logger.warning(
                            'Attempt to update demand in move %s related to POS %s (skip_inventory_moves activated). '
                            'Update has been blocked (POS should not affect inventory).',
                            move.name, pos_order.config_id.name
                        )
                        break
                
                if not should_block:
                    moves_to_assign |= move
            else:
                moves_to_assign |= move
        
        # Pasar el argumento force_qty si fue proporcionado
        if force_qty is not None:
            return super(StockMove, moves_to_assign)._action_assign(force_qty=force_qty)
        else:
            return super(StockMove, moves_to_assign)._action_assign()

    def write(self, vals):
        """Override write para prevenir actualización de cantidad cuando está relacionado con POS
        y skip_inventory_moves está activado
        NOTA: Solo bloqueamos si el picking viene DIRECTAMENTE del POS, no si viene de una orden de venta normal
        También bloqueamos si el picking ya está en estado 'done' (ya fue despachado)"""
        # Si se está intentando actualizar la cantidad, verificar si está relacionado con POS
        if 'product_uom_qty' in vals or 'reserved_availability' in vals:
            pos_moves_to_block = self.env['stock.move']
            other_moves = self.env['stock.move']
            
            for move in self:
                # Si el picking viene de una orden de venta normal (tiene sale_id)
                if move.picking_id and move.picking_id.sale_id:
                    # Si el picking ya está en estado 'done' (ya fue despachado)
                    if move.picking_id.state == 'done':
                        # Si hay un contexto especial que indica que estamos restaurando, permitir
                        if self.env.context.get('_skip_inventory_block'):
                            other_moves |= move
                            continue
                        # Si se está intentando poner la cantidad en 0, bloquear (el código de pos_sale está actualizando)
                        # Pero si se está restaurando una cantidad mayor a 0, permitir (estamos restaurando)
                        new_qty = vals.get('product_uom_qty', move.product_uom_qty)
                        if new_qty == 0:
                            _logger.info(
                                'Intento de actualizar cantidad a 0 en movimiento %s de picking %s que ya está en estado "done". '
                                'La actualización ha sido bloqueada (picking ya fue despachado, POS solo debe cobrar).',
                                move.name, move.picking_id.name
                            )
                            pos_moves_to_block |= move
                            continue
                        # Si se está restaurando una cantidad > 0, permitir
                        else:
                            other_moves |= move
                            continue
                    # Si el picking no está en 'done', permitir actualización normal
                    other_moves |= move
                    continue
                
                pos_orders = self._get_related_pos_orders(move)
                if pos_orders:
                    # Verificar si alguno de los POS relacionados tiene skip_inventory_moves activado
                    should_block = False
                    for pos_order in pos_orders:
                        config = pos_order.config_id.sudo()
                        skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
                        if skip_inventory:
                            should_block = True
                            _logger.warning(
                                'Intento de actualizar cantidad en movimiento %s relacionado con POS %s (skip_inventory_moves activado). '
                                'La actualización ha sido bloqueada (POS no debe afectar inventario).',
                                move.name, pos_order.config_id.name
                            )
                            break
                    
                    if should_block:
                        pos_moves_to_block |= move
                    else:
                        other_moves |= move
                else:
                    other_moves |= move
            
            # Crear un nuevo vals sin los campos de cantidad para los movimientos del POS bloqueados
            if pos_moves_to_block:
                pos_vals = vals.copy()
                pos_vals.pop('product_uom_qty', None)
                pos_vals.pop('reserved_availability', None)
                
                # Actualizar movimientos del POS sin los campos de cantidad
                if pos_vals:
                    super(StockMove, pos_moves_to_block).write(pos_vals)
            
            # Actualizar movimientos normales con todos los valores
            if other_moves:
                return super(StockMove, other_moves).write(vals)
            else:
                return True
        
        return super(StockMove, self).write(vals)
