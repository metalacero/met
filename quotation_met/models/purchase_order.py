# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    company_stamp = fields.Binary(string="Sello", attachment=True)
    company_signature = fields.Binary(string="Firma", attachment=True)

    def get_company_stamp(self):
        """
        Retorna el sello de la orden de compra o el sello por defecto si no tiene uno asignado.
        Similar a como se hace en account.move.
        """
        if self.company_stamp:
            return self.company_stamp
        
        # Si no tiene sello, obtener el sello por defecto
        stamp_attachment = self.env.ref(
            "l10n_do_accounting.default_invoice_stamp",
            raise_if_not_found=False,
        )
        if stamp_attachment:
            return stamp_attachment.sudo().datas
        
        return None

    def get_company_signature(self):
        """
        Retorna la firma de la orden de compra o la firma por defecto si no tiene una asignada.
        """
        if self.company_signature:
            return self.company_signature

        signature_attachment = self.env.ref(
            "quotation_met.default_purchase_signature",
            raise_if_not_found=False,
        )
        if signature_attachment:
            return signature_attachment.sudo().datas

        return None

    def button_confirm(self):
        """Override to set default company stamp when confirming purchase order"""
        result = super(PurchaseOrder, self).button_confirm()
        
        # Set default company stamp for purchase orders
        stamp_attachment = self.env.ref(
            "l10n_do_accounting.default_invoice_stamp",
            raise_if_not_found=False,
        )
        if stamp_attachment:
            for order in self:
                if not order.company_stamp:
                    order.company_stamp = stamp_attachment.datas

        # Set default company signature for purchase orders
        signature_attachment = self.env.ref(
            "quotation_met.default_purchase_signature",
            raise_if_not_found=False,
        )
        if signature_attachment:
            for order in self:
                if not order.company_signature:
                    order.company_signature = signature_attachment.datas

        return result
