import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    measurement = fields.Float(string="Medida")

    def _get_move_raw_values(
        self,
        product_id,
        product_uom_qty,
        product_uom,
        operation_id=False,
        bom_line=False,
    ):
        data = super()._get_move_raw_values(
            product_id, product_uom_qty, product_uom, operation_id, bom_line
        )
        _logger.info(f"Scale up {data['product_uom_qty']} by {self.measurement}")
        if self.measurement:
            data["product_uom_qty"] = data["product_uom_qty"] * self.measurement
        return data
