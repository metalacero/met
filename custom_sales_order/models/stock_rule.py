import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    """
        Override the manufacturing rule to addition a dynamically generated measurement from the sale order line.
    """

    @api.model
    def _run_manufacture(self, procurements):
        for procurement, rule in procurements:
            group = procurement.values.get("group_id")
            if group and isinstance(group, self.env["procurement.group"].__class__):
                domain = [
                    ("order_id.procurement_group_id", "=", group.id),
                    ("product_id", "=", procurement.product_id.id),
                ]
                so_line = self.env["sale.order.line"].search(domain, limit=1)
                if so_line:
                    procurement.values["measurement"] = so_line.measurement
        super(StockRule, self)._run_manufacture(procurements)

    """
        Prepare the manufacturing order values.
    """

    def _prepare_mo_vals(
        self,
        product_id,
        product_qty,
        product_uom,
        location_dest_id,
        name,
        origin,
        company_id,
        values,
        bom,
    ):
        vals = super()._prepare_mo_vals(
            product_id,
            product_qty,
            product_uom,
            location_dest_id,
            name,
            origin,
            company_id,
            values,
            bom,
        )
        if bom:
            vals["measurement"] = values.get("measurement", 0)
        _logger.info(f"MO values passed into new make order: {vals}")
        return vals
