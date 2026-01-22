from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    skip_inventory_moves = fields.Boolean(
        related='pos_config_id.skip_inventory_moves',
        readonly=False,
        string='No afectar inventario',
        help='Si está activado, las ventas del POS no afectarán el inventario ni crearán órdenes de salida'
    )