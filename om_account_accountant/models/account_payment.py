# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    effective_date = fields.Date(
        string='Effective Date',
        help='Effective date of payment',
        copy=False,
    )
