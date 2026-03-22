from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    measurement = fields.Float(string="Medida")
