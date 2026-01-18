from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    measurement = fields.Float(string="Medida", default=1)
    variable_measurement = fields.Boolean(string="Producto a medida", default=False)
