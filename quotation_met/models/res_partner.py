# # -*- coding: utf-8 -*-

# from odoo import models, api


# class ResPartner(models.Model):
#     _inherit = 'res.partner'

#     @api.model
#     def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
#         """Override _name_search to filter by customer/supplier based on context"""
#         # Ensure args is a list
#         if args is None:
#             args = []
#         elif not isinstance(args, (list, tuple)):
#             args = []
#         else:
#             args = list(args)  # Convert to list to avoid tuple issues
        
#         # Check if we're in a sales context (customer mode)
#         search_mode = self.env.context.get('res_partner_search_mode')
#         if search_mode == 'customer':
#             # Filter to show only customers: customer_rank > 0 OR supplier_rank = 0
#             # This excludes partners that are ONLY suppliers
#             domain = ['|', ('customer_rank', '>', 0), ('supplier_rank', '=', 0)]
#             # Combine domain with existing args using AND
#             args = domain + args
#         # Check if we're in a purchase context (supplier mode)
#         elif search_mode == 'supplier':
#             # Filter to show only suppliers: supplier_rank > 0 OR customer_rank = 0
#             # This excludes partners that are ONLY customers
#             domain = ['|', ('supplier_rank', '>', 0), ('customer_rank', '=', 0)]
#             # Combine domain with existing args using AND
#             args = domain + args
        
#         # Ensure we always return a valid result
#         try:
#             return super(ResPartner, self)._name_search(name, args, operator, limit, order)
#         except Exception:
#             # Fallback to default behavior if there's an error
#             return super(ResPartner, self)._name_search(name, [], operator, limit, order)
