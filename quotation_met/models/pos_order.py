from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    skip_inventory_moves = fields.Boolean(
        string='No afectar inventario',
        default=False,
        help='Si está activado, las ventas del POS no afectarán el inventario ni crearán órdenes de salida'
    )