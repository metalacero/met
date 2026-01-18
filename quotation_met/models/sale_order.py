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

    payment_method_id = fields.Many2one(
        string='Método de Pago',
        comodel_name='account.payment.method',
        domain=[('payment_type', '=', 'inbound')],
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

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """filter sale orders to credit when searching from the POS"""
        # verify if the user has a POS session opened
        # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            
            # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
            if pos_session and 'invoice_type' in self.env['sale.order']._fields:
                domain = domain or []
                # add the condition to exclude invoice_type = 'credito'
                domain = domain + [('invoice_type', '!=', 'credito')]
                _logger.info('Filtering sale orders from POS (search_read): excluding invoice_type=credito')
        except Exception as e:
            _logger.debug('Error verifying POS session: %s', str(e))
        
        return super(SaleOrder, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """filter sale orders to credit when searching from the POS"""
        # verify if the user has a POS session opened
        # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            
            # if the user has a POS session opened, apply the filter to exclude invoice_type = 'credito'
            if pos_session and 'invoice_type' in self.env['sale.order']._fields:
                domain = domain or []
                # add the condition to exclude invoice_type = 'credito'
                domain = domain + [('invoice_type', '!=', 'credito')]
                _logger.info('Filtering sale orders from POS (search): excluding invoice_type=credito')
        except Exception as e:
            _logger.debug('Error verifying POS session: %s', str(e))
        
        return super(SaleOrder, self).search(domain, offset=offset, limit=limit, order=order)

    