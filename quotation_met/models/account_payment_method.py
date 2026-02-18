# -*- coding: utf-8 -*-

from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    @api.model
    def _get_payment_method_information(self):
        """Registrar los métodos de pago personalizados para que se añadan a los diarios.
        Sin esto, solo aparecería 'Manual' al configurar los diarios."""
        info = super()._get_payment_method_information()
        # Añadir métodos con mode='multi' para que se creen líneas en todos los diarios bank/cash
        manual_config = info.get('manual', {'mode': 'multi', 'domain': [('type', 'in', ('bank', 'cash'))]})
        for code in ('transferencia', 'tarjeta_credito', 'tarjeta_debito', 'efectivo', 'cheque', 'deposito'):
            info[code] = manual_config
        return info

    @api.model
    def _register_hook(self):
        """Al iniciar, asegurar que los métodos personalizados estén en los diarios (para instalaciones existentes)."""
        res = super()._register_hook()
        try:
            PaymentMethodLine = self.env['account.payment.method.line']
            PaymentMethod = self.env['account.payment.method']
            Journal = self.env['account.journal']

            journals = Journal.search([('type', 'in', ('bank', 'cash'))])
            custom_methods = PaymentMethod.search([
                ('code', 'in', ('transferencia', 'tarjeta_credito', 'tarjeta_debito', 'efectivo', 'cheque', 'deposito')),
                ('payment_type', '=', 'inbound'),
            ])

            for journal in journals:
                for method in custom_methods:
                    existing = PaymentMethodLine.search([
                        ('journal_id', '=', journal.id),
                        ('payment_method_id', '=', method.id),
                    ], limit=1)
                    if not existing:
                        PaymentMethodLine.create({
                            'name': method.name,
                            'payment_method_id': method.id,
                            'journal_id': journal.id,
                        })
        except Exception:
            pass  # Evitar fallos en arranque (ej. sin DB aún)
        return res
