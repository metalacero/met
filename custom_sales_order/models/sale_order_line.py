from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
        store=False,
    )

    price_per_measurement = fields.Float(string="Precio por pie")

    # Dynamic pricing based on feet length
    @api.onchange("product_uom_qty", "measurement", "price_per_measurement")
    def _compute_variable_length_price(self):
        self.ensure_one()

        if self.product_id.variable_measurement:
            self.price_unit = self.measurement * self.price_per_measurement

    # Feet length and price per foot constraints
    @api.constrains("length_in_feet", "price_per_foot")
    def _check_feet_length_and_price(self):
        self.ensure_one()
        if self.product_id.variable_measurement:
            if self.measurement <= 0 or self.price_per_measurement <= 0:
                raise ValidationError(
                    "Medida y precio por pie deben ser mayores que cero."
                )

    # Prepare values to send to INV/MRP
    def _prepare_procurement_values(self):
        self.ensure_one()

        values = super()._prepare_procurement_values()
        if self.product_id.variable_measurement:
            values["measurement"] = self.measurement
        return values
