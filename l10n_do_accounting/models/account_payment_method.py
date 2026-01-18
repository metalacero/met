from odoo import api, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"


    @api.model
    def _get_payment_method_information(self):
        info = super()._get_payment_method_information()

        # Add new payment method codes that behaves semantically similar to the manual code.
        # Used for bank/cash journal
        info['bank_transfer'] = info['manual']
        info['cash'] = info['manual']
        info['credit_card'] = info['manual']
        info['debit_card'] = info['manual']
        info['bank_deposit'] = info['manual']
        return info
