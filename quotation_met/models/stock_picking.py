# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_cancel(self):
        """Override action_cancel to prevent the cancellation of pickings related to POS.
        The POS should only create invoices and apply payments, without affecting inventory.
        NOTE: We only block if the picking comes DIRECTLY from a POS order, not if it comes from a regular sale order."""
        for picking in self:
            # Si el picking viene de una orden de venta normal (tiene sale_id), no bloquear
            # Las órdenes de venta normales deben funcionar normalmente
            if picking.sale_id:
                # Viene de una orden de venta normal, permitir cancelación normal
                continue
            
            # Verificar si está relacionado con POS y si skip_inventory_moves está activado
            pos_orders = self._get_related_pos_orders(picking)
            
            if pos_orders:
                # Verificar si alguno de los POS relacionados tiene skip_inventory_moves activado
                for pos_order in pos_orders:
                    config = pos_order.config_id.sudo()
                    skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
                    if skip_inventory:
                        _logger.warning(
                            'Intento de cancelar picking %s relacionado con POS %s (skip_inventory_moves activado). '
                            'La cancelación ha sido bloqueada silenciosamente (POS no debe afectar inventario).',
                            picking.name, pos_order.config_id.name
                        )
                        return False  # Bloquear cancelación sin mostrar error
        
        return super(StockPicking, self).action_cancel()

    def _get_related_pos_orders(self, picking):
        """Get all POS orders related to a picking"""
        pos_orders = self.env['pos.order']
        
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
        if picking.move_ids:
            product_ids = picking.move_ids.mapped('product_id').ids
            
            if product_ids:
                # Search for invoices that contain these products and are related to POS
                invoice_lines = self.env['account.move.line'].sudo().search([
                    ('product_id', 'in', product_ids),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('move_id.state', '=', 'posted')
                ])
                
                invoices = invoice_lines.mapped('move_id')
                
                for invoice in invoices:
                    pos_order = self.env['pos.order'].sudo().search([
                        ('account_move', '=', invoice.id)
                    ], limit=1)
                    
                    if pos_order:
                        # Check if the relation is valid
                        is_related = False
                        if picking.partner_id and invoice.partner_id:
                            is_related = (picking.partner_id == invoice.partner_id)
                        
                        if not is_related and picking.scheduled_date and invoice.invoice_date:
                            date_diff = abs((picking.scheduled_date.date() - invoice.invoice_date).days)
                            is_related = (date_diff <= 1)
                        
                        if is_related:
                            pos_orders |= pos_order
                
                # Verificar órdenes del POS con pagos aplicados
                if picking.partner_id:
                    date_limit = datetime.now() - timedelta(days=1)
                    
                    found_pos_orders = self.env['pos.order'].sudo().search([
                        ('state', 'in', ['paid', 'done', 'invoiced']),
                        ('partner_id', '=', picking.partner_id.id),
                        ('date_order', '>=', date_limit),
                        ('payment_ids', '!=', False)
                    ])
                    
                    for pos_order in found_pos_orders:
                        pos_product_ids = set(pos_order.lines.mapped('product_id').ids)
                        picking_product_ids = set(product_ids)
                        
                        if picking_product_ids & pos_product_ids:
                            pos_date = pos_order.date_order.date() if pos_order.date_order else None
                            picking_date = picking.scheduled_date.date() if picking.scheduled_date else None
                            
                            date_match = False
                            if pos_date and picking_date:
                                date_diff = abs((picking_date - pos_date).days)
                                date_match = (date_diff <= 1)
                            
                            if date_match or not picking_date:
                                pos_orders |= pos_order
        
        return pos_orders
    
    def _is_related_to_pos(self, picking):
        """Verificar si un picking está relacionado con el POS"""
        pos_orders = self._get_related_pos_orders(picking)
        return bool(pos_orders)

    def button_validate(self):
        """Override button_validate to prevent the picking from being marked as done when it is related to POS.
        The POS should only create invoices and apply payments, without affecting inventory.
        NOTE: We only block if the picking comes DIRECTLY from a POS order, not if it comes from a regular sale order."""
        for picking in self:
            # If the picking comes from a regular sale order (has sale_id), don't block
            # Regular sale orders should work normally
            if picking.sale_id:
                # Comes from a regular sale order, allow validation normally
                continue
            
            pos_orders = self._get_related_pos_orders(picking)
            if pos_orders:
                # Check if any of the related POS orders have skip_inventory_moves activated
                for pos_order in pos_orders:
                    config = pos_order.config_id.sudo()
                    skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
                    if skip_inventory:
                        _logger.warning(
                            'Attempt to validate picking %s related to POS %s (skip_inventory_moves activated). '
                            'Validation has been blocked silently (POS should not affect inventory).',
                            picking.name, pos_order.config_id.name
                        )
                        return False  # Block validation without showing error
        
        return super(StockPicking, self).button_validate()

    def action_done(self):
        """Override action_done to prevent the picking from being marked as done when it is related to POS.
        The POS should only create invoices and apply payments, without affecting inventory.
        NOTE: We only block if the picking comes DIRECTLY from a POS order, not if it comes from a regular sale order."""
        for picking in self:
            # If the picking comes from a regular sale order (has sale_id), don't block
            # Regular sale orders should work normally
            if picking.sale_id:
                # Comes from a regular sale order, allow action normally
                continue
            
            pos_orders = self._get_related_pos_orders(picking)
            if pos_orders:
                # Check if any of the related POS orders have skip_inventory_moves activated
                for pos_order in pos_orders:
                    config = pos_order.config_id.sudo()
                    skip_inventory = config.read(['skip_inventory_moves'])[0].get('skip_inventory_moves', False)
                    if skip_inventory:
                        _logger.warning(
                            'Attempt to mark picking %s related to POS %s (skip_inventory_moves activated). '
                            'Action has been blocked silently (POS should not affect inventory).',
                            picking.name, pos_order.config_id.name
                        )
                        return False  # Bloquear sin mostrar error
        
        return super(StockPicking, self).action_done()
