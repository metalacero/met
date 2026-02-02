# -*- coding: utf-8 -*-

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_populogo_image(self):
        """
        Retorna la imagen populogo.jpg desde ir.attachment, igual que company_stamp.
        Este método devuelve el campo 'datas' (binario en base64) del ir.attachment.
        """
        populogo_attachment = self.env.ref(
            "l10n_do_accounting.populogo_image",
            raise_if_not_found=False,
        )
        if populogo_attachment:
            return populogo_attachment.datas
        return None
