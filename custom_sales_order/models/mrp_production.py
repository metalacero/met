from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    measurement = fields.Float(string="Medida (en pies)")
