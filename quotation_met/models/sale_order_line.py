import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Campo relacionado del producto para controlar si el precio es modificable
    price_modifiable = fields.Boolean(
        related="product_id.price_modifiable",
        string="Precio Modificable",
        readonly=True,
        store=False,
    )

    @api.depends(
        'pos_order_line_ids.qty',
        'pos_order_line_ids.order_id.picking_ids',
        'pos_order_line_ids.order_id.picking_ids.state',
    )
    def _compute_qty_delivered(self):
        """
        Prevent double-counting qty_delivered when a sale order line is settled
        via POS but also has a validated stock picking from the warehouse.
        Both pos_sale and stock independently add to qty_delivered, which can
        result in values like 4 when only 2 were ordered.
        Cap at product_uom_qty whenever POS lines are present and the value
        exceeds the ordered quantity.
        """
        super()._compute_qty_delivered()
        for line in self:
            if line.pos_order_line_ids and line.qty_delivered > line.product_uom_qty:
                line.qty_delivered = line.product_uom_qty

    def read_converted(self):
        """
        Override to allow POS to settle a sale order line even when the
        warehouse delivery (stock picking) was validated before POS payment.

        The base pos_sale JS (setQuantityFromSOL) computes:
            quantity = product_uom_qty - max(qty_delivered, qty_invoiced)

        When the picking is already done (qty_delivered == product_uom_qty)
        but the line has NOT yet been settled via POS, that formula gives 0
        and the line appears empty/missing in the settle dialog.

        Fix: mask qty_delivered as 0 for lines that have not yet been settled
        via POS (no pos_order_line_ids), so the JS formula yields the full
        product_uom_qty and the cashier can complete the payment.
        """
        results = super().read_converted()
        # Build set of line IDs already partially/fully settled via POS
        settled_ids = set(self.filtered(lambda l: l.pos_order_line_ids).ids)
        for item in results:
            if item.get("id") not in settled_ids:
                item["qty_delivered"] = 0.0
        return results

    @api.model
    def _get_product_domain(self):
        """Filtrar productos restringidos en las líneas de venta"""
        # DESACTIVADO: Restricción de productos por usuario deshabilitada
        domain = []
        # user = self.env.user

        # # if user is not admin, filter restricted products
        # if not user.has_group('base.group_system'):
        #     domain = [
        #         '|',
        #         ('is_restricted_user', '=', False),
        #         '|',
        #         ('restricted_user_id', '=', False),
        #         ('restricted_user_id', '=', user.id)
        #     ]

        return domain
