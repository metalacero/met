# -*- coding: utf-8 -*-

from odoo import models, fields, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    bank_reference = fields.Char(
        string='Referencia Bancaria',
        help='Referencia bancaria del pago',
        copy=False,
    )

    cheque_reference = fields.Char(
        string='Referencia de Cheque',
        help='Referencia del cheque del pago',
        copy=False,
    )

