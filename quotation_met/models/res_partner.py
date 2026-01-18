# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_type = fields.Selection(
        string='Condiciones de Pago',
        selection=[('contado', 'Al Contado'), ('credito', 'A Crédito')],
        default='credito',
        help='Condiciones de pago predeterminadas para este cliente',
        copy=False,
    )
