# -*- coding: utf-8 -*-

from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_populogo_image(self):
        """
        Retorna la imagen populogo.jpg desde ir.attachment, igual que company_stamp.
        Este método devuelve el campo 'datas' (binario en base64) del ir.attachment.
        Usa sudo() para evitar problemas de permisos durante la generación de reportes.
        """
        populogo_attachment = self.env.ref(
            "l10n_do_accounting.populogo_image",
            raise_if_not_found=False,
        )
        if populogo_attachment:
            return populogo_attachment.sudo().datas
        return None
