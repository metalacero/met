# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fecha_entrega = fields.Date(
        string='Fecha de Entrega',
        help='Fecha de entrega del pedido',
        copy=False,
        required=True,
    )

    # payment_method_id = fields.Many2one(
    #     string='Método de Pago',
    #     comodel_name='account.payment.method',
    #     domain=[('payment_type', '=', 'inbound')],
    #     help='Método de pago que se utilizará al facturar. Selecciona el método de pago (Efectivo, Transferencia, Tarjeta, etc.)',
    #     copy=False,
    # )

    payment_method = fields.Selection(
        string='Método de Pago',
        selection=[('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'), ('tarjeta', 'Tarjeta Credito / Debito')],
        default='efectivo',
        help='Método de pago que se utilizará al facturar. Selecciona el método de pago (Efectivo, Transferencia, Tarjeta, etc.)',
        copy=False,
    )

    invoice_type = fields.Selection(
        string='Condiciones de Pago',
        selection=[('contado', 'Al Contado'), ('credito', 'A Crédito')],
        default='credito',
        help='Indica si la venta es al contado o a crédito',
        copy=True,
        required=True,
    )


    # Campos relacionados para mostrar dirección y teléfono
    partner_street = fields.Char(related='partner_id.street', string='Calle', readonly=True, store=False)
    partner_street2 = fields.Char(related='partner_id.street2', string='Calle 2', readonly=True, store=False)
    partner_city = fields.Char(related='partner_id.city', string='Ciudad', readonly=True, store=False)
    partner_state_id = fields.Many2one(related='partner_id.state_id', string='Estado', readonly=True, store=False)
    partner_zip = fields.Char(related='partner_id.zip', string='Código Postal', readonly=True, store=False)
    partner_country_id = fields.Many2one(related='partner_id.country_id', string='País', readonly=True, store=False)
    partner_phone = fields.Char(related='partner_id.phone', string='Teléfono', readonly=True, store=False)
    partner_mobile = fields.Char(related='partner_id.mobile', string='Móvil', readonly=True, store=False)
    
    #onchange para calcular la fecha de vencimiento
    @api.onchange('date_order')
    def _onchange_date_order(self):
        if self.date_order:
            # date_order es datetime, necesitamos convertir a date para sumar días
            if isinstance(self.date_order, datetime):
                date_order_date = self.date_order.date()
            else:
                date_order_date = self.date_order
            self.validity_date = date_order_date + timedelta(days=3)
            _logger.info('Fecha de entrega: %s', self.validity_date)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """set the invoice_type to the partner's invoice_type"""
        if self.partner_id and self.partner_id.invoice_type:
            self.invoice_type = self.partner_id.invoice_type
            _logger.info('Tipo de factura traído del cliente: %s', self.invoice_type)

    @api.onchange('invoice_type')
    def _onchange_invoice_type(self):
        """set the immediate payment term when it is in cash"""
        if self.invoice_type == 'contado':
            # Buscar el término de pago inmediato
            immediate_payment_term = self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False)
            if immediate_payment_term:
                self.payment_term_id = immediate_payment_term
                _logger.info('Término de pago establecido a inmediato para orden al contado')

    def _action_confirm(self):
        """Verify if the requested quantities exist in inventory before confirming"""
        for order in self:
            for line in order.order_line:
                if line.product_id:
                    # Verify if the product is stockable (has inventory control)
                    product_type = getattr(line.product_id, 'detailed_type', None) or getattr(line.product_id, 'type', None)
                    
                    if product_type == 'product':
                        # ignore products manufactured (have manufacturing route)
                        product = line.product_id
                        # verify if the product has a manufacturing route
                        has_manufacturing_route = False
                        if hasattr(product, 'route_ids'):
                            manufacturing_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
                            if manufacturing_route and manufacturing_route in product.route_ids:
                                has_manufacturing_route = True
                        
                        # verify inventory if the product is not manufactured
                        if not has_manufacturing_route:
                            # Use the warehouse of the order if available
                            if order.warehouse_id:
                                product = product.with_context(warehouse=order.warehouse_id.id)
                            
                            # get the available quantity
                            qty_available = product.qty_available
                            
                            # Verify if there is enough inventory
                            if qty_available < line.product_uom_qty:
                                raise UserError(_(
                                    'No hay suficiente inventario para el producto "%s".\n'
                                    'Cantidad solicitada: %s %s\n'
                                    'Cantidad disponible: %s %s'
                                ) % (
                                    line.product_id.display_name,
                                    line.product_uom_qty,
                                    line.product_uom.name if line.product_uom else '',
                                    qty_available,
                                    line.product_id.uom_id.name if line.product_id.uom_id else ''
                                ))
        
        return super(SaleOrder, self)._action_confirm()

    def _prepare_invoice(self):
        """Override to copy invoice_type field to invoice"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['invoice_type'] = self.invoice_type
        _logger.info('Orden de venta %s: Preparando factura con invoice_type=%s, payment_method_id=%s', 
                    self.name, self.invoice_type, 
                    self.payment_method_id.name if self.payment_method_id else 'NO CONFIGURADO')
        return invoice_vals

    def read(self, fields=None, load='_classic_read'):
        """Override read to ensure order_line is always included when reading from POS"""
        # Check if this is being called from POS context
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            
            # If called from POS and fields are specified, ensure order_line is included
            if pos_session and fields is not None:
                fields = list(fields) if isinstance(fields, (list, tuple)) else [fields]
                if 'order_line' not in fields:
                    fields.append('order_line')
        except Exception as e:
            _logger.debug('Error verifying POS session in read: %s', str(e))
        
        result = super(SaleOrder, self).read(fields=fields, load=load)
        
        # Ensure order_line exists in result (set to empty list if missing)
        if isinstance(result, list):
            for record in result:
                if isinstance(record, dict) and 'order_line' not in record:
                    record['order_line'] = []
                # Si estamos en contexto POS y hay order_line, consolidar líneas duplicadas
                elif isinstance(record, dict) and 'order_line' in record and pos_session:
                    record['order_line'] = self._consolidate_order_lines_for_pos(record.get('id'))
        elif isinstance(result, dict) and 'order_line' not in result:
            result['order_line'] = []
        elif isinstance(result, dict) and 'order_line' in result and pos_session:
            # Consolidar líneas duplicadas para POS
            result['order_line'] = self._consolidate_order_lines_for_pos(result.get('id'))
        
        return result
    
    def _consolidate_order_lines_for_pos(self, order_id):
        """
        Consolida líneas de venta duplicadas del mismo producto antes de enviarlas al POS
        """
        if not order_id:
            return []
        
        order = self.browse(order_id)
        if not order.exists():
            return []
        
        # Agrupar líneas por producto_id
        lines_by_product = {}
        for line in order.order_line:
            if not line.product_id:
                continue
            
            product_id = line.product_id.id
            if product_id not in lines_by_product:
                lines_by_product[product_id] = []
            lines_by_product[product_id].append(line.id)
        
        # Si hay líneas duplicadas, consolidarlas
        consolidated_line_ids = []
        for product_id, line_ids in lines_by_product.items():
            if len(line_ids) > 1:
                # Hay múltiples líneas del mismo producto, usar solo la primera
                # El método read_converted se encargará de consolidar las cantidades
                consolidated_line_ids.append(line_ids[0])
                _logger.info(
                    'Consolidando %s líneas del producto %s en POS, usando línea %s',
                    len(line_ids), product_id, line_ids[0]
                )
            else:
                consolidated_line_ids.append(line_ids[0])
        
        return consolidated_line_ids

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """filter sale orders to credit when searching from the POS"""
        # verify if the user has a POS session opened
        # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
        # and exclude quotations (only show confirmed sale orders with state = 'sale')
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            
            if pos_session:
                domain = domain or []
                
                # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
                if 'invoice_type' in self.env['sale.order']._fields:
                    # add the condition to exclude invoice_type = 'credito'
                    domain = domain + [('invoice_type', '!=', 'credito')]
                    _logger.info('Filtering sale orders from POS (search_read): excluding invoice_type=credito')
                
                # Exclude quotations (draft, sent) - only show confirmed sale orders
                domain = domain + [('state', '=', 'sale')]
                _logger.info('Filtering sale orders from POS (search_read): excluding quotations, only showing confirmed orders')
            
            # Ensure order_line is included when reading from POS
            if pos_session and fields is not None:
                fields = list(fields) if isinstance(fields, (list, tuple)) else fields
                if isinstance(fields, list) and 'order_line' not in fields:
                    fields.append('order_line')
        except Exception as e:
            _logger.debug('Error verifying POS session: %s', str(e))
        
        result = super(SaleOrder, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        
        # Ensure order_line exists in all results (set to empty list if missing)
        if isinstance(result, list):
            for record in result:
                if isinstance(record, dict) and 'order_line' not in record:
                    record['order_line'] = []
        
        return result

    @api.model
    def search(self, domain, offset=0, limit=None, order=None, count=False):
        """filter sale orders to credit when searching from the POS"""
        # verify if the user has a POS session opened
        # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
        # and exclude quotations (only show confirmed sale orders with state = 'sale')
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            
            if pos_session:
                domain = domain or []
                
                # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
                if 'invoice_type' in self.env['sale.order']._fields:
                    # add the condition to exclude invoice_type = 'credito'
                    domain = domain + [('invoice_type', '!=', 'credito')]
                    _logger.info('Filtering sale orders from POS (search): excluding invoice_type=credito')
                
                # Exclude quotations (draft, sent) - only show confirmed sale orders
                domain = domain + [('state', '=', 'sale')]
                _logger.info('Filtering sale orders from POS (search): excluding quotations, only showing confirmed orders')
        except Exception as e:
            _logger.debug('Error verifying POS session: %s', str(e))
        
        return super(SaleOrder, self).search(domain, offset=offset, limit=limit, order=order, count=count)

    