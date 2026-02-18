# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection(
        string='Condiciones de Pago',
        selection=[('contado', 'Al Contado'), ('credito', 'A Crédito')],
        default='credito',
        help='Indica si la factura es al contado o a crédito',
        copy=False,
        required=True,
    )

    applied_payment_method_id = fields.Many2one(
        string='Método de Pago (aplicado)',
        comodel_name='account.payment.method',
        compute='_compute_applied_payment_info',
        help='Método de pago usado al registrar el pago en la factura',
        readonly=True,
    )

    @api.depends(
        'line_ids.matched_debit_ids',
        'line_ids.matched_credit_ids',
        'line_ids.account_id',
        'payment_state',
    )
    def _compute_applied_payment_info(self):
        for move in self:
            move.applied_payment_method_id = False
            if move.payment_state not in ('paid', 'partial', 'in_payment'):
                continue
            if move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                continue
            # Obtener pagos reconciliados desde las líneas de la factura
            rec_lines = move.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            payments = self.env['account.payment']
            for line in rec_lines:
                for partial in line.matched_debit_ids | line.matched_credit_ids:
                    counterpart = (
                        partial.credit_move_id if partial.debit_move_id == line
                        else partial.debit_move_id
                    )
                    if counterpart.move_id.payment_id:
                        payments |= counterpart.move_id.payment_id
            if payments:
                last_payment = payments.sorted('date', reverse=True)[0]
                move.applied_payment_method_id = last_payment.payment_method_id

    @api.model
    def default_get(self, fields_list):
        """set invoice_date to today for all invoices and invoice_type to 'contado' for POS invoices"""
        res = super(AccountMove, self).default_get(fields_list)
        # only for invoices (out_invoice, in_invoice, out_refund, in_refund)
        move_type = res.get('move_type') or self.env.context.get('default_move_type')
        if move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
            if 'invoice_date' in fields_list:
                res['invoice_date'] = fields.Date.context_today(self)
            
            # if invoice_type is in fields_list, verify if the user has a POS session opened
            # verify if the user has a POS session opened
            if 'invoice_type' in fields_list:
                try:
                    pos_session = self.env['pos.session'].sudo().search([
                        ('user_id', '=', self.env.uid),
                        ('state', '=', 'opened')
                    ], limit=1)
                    if pos_session:
                        res['invoice_type'] = 'contado'
                        _logger.info('Invoice created from POS: setting invoice_type=contado')
                except Exception as e:
                    _logger.debug('Error verifying POS session in default_get: %s', str(e))
        
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Set invoice_type to 'contado' for invoices created from POS"""
        # verify if the user has a POS session opened before creating the invoice
        is_from_pos = False
        try:
            pos_session = self.env['pos.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('state', '=', 'opened')
            ], limit=1)
            if pos_session:
                is_from_pos = True
        except Exception:
            pass
        
        # if the invoice is from POS, set invoice_type = 'contado' for all invoices
        if is_from_pos:
            for vals in vals_list:
                move_type = vals.get('move_type') or self.env.context.get('default_move_type')
                if move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                    vals['invoice_type'] = 'contado'
                    _logger.info('Factura creada desde POS: estableciendo invoice_type=contado')
        
        invoices = super(AccountMove, self).create(vals_list)
        
        # also verify after creating if the invoice is related to a POS order
        for invoice in invoices:
            if invoice.move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
                # verify if the invoice is related to a POS order
                pos_order = self.env['pos.order'].sudo().search([
                    ('account_move', '=', invoice.id)
                ], limit=1)
                
                if pos_order and invoice.invoice_type == 'credito':
                    invoice.invoice_type = 'contado'
                    _logger.info('Factura %s relacionada con POS order: estableciendo invoice_type=contado', invoice.name)
        
        return invoices
