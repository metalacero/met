# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def _get_product_domain(self):
        """Filtrar productos restringidos en las líneas de factura"""
        domain = []
        user = self.env.user
        
        # if user is not admin, filter restricted products
        if not user.has_group('base.group_system'):
            domain = [
                '|',
                ('is_restricted_user', '=', False),
                '|',
                ('restricted_user_id', '=', False),
                ('restricted_user_id', '=', user.id)
            ]
        
        return domain

