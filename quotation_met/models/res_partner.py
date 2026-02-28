# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    invoice_type = fields.Selection(
        string="Condiciones de Pago",
        selection=[("contado", "Al Contado"), ("credito", "A Crédito")],
        default="credito",
        help="Condiciones de pago predeterminadas para este cliente",
        copy=False,
    )

    ignore_fiscal_type = fields.Boolean(
        string="Ignorar Tipo Fiscal",
        default=False,
        help="Ignora el tipo fiscal predeterminado para este cliente",
        copy=False,
    )

    # @api.depends("sale_fiscal_type_id", "country_id", "parent_id", "ignore_fiscal_type")
    # def _compute_is_fiscal_info_required(self):
    #     for partner in self:
    #         partner.is_fiscal_info_required = (
    #             not partner.ignore_fiscal_type
    #             and bool(partner.sale_fiscal_type_id)
    #             and partner.sale_fiscal_type_id.requires_document
    #             and partner.country_id == self.env.ref("base.do")
    #             and not partner.parent_id
    #         )
