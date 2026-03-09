import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    measurement = fields.Float(
        related="product_id.measurement",
        string="Medida",
        store=True,
        readonly=False,
    )

    variable_measurement = fields.Boolean(
        related="product_id.variable_measurement",
        string="Producto a medida",
        store=True,
    )

    # Prepare values to send to INV/MRP
    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()

        _logger.info("Measurement value: %s", self.measurement)
        _logger.info("Variable measurement ? %s", self.variable_measurement)
        if self.variable_measurement:
            values["measurement"] = self.measurement
        _logger.info(f"Procurement values: {values}")
        return values
