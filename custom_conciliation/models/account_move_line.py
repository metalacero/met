
from odoo import models
from odoo.exceptions import UserError, MissingError
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_reconcile_payment_with_statement(self):
        if len(self) != 2:
            raise UserError('Debe conciliar exactamente 2 apuntes contables.')

        # Account for reconcile banking transactions
        BANK_SUSPENSE_ACCOUNT_CODE = "11010201"

        # Account for holding customer funds not yet confirmed.
        OUTSTANDING_RECEIPTS_ACCOUNT_CODE = "11010202"

        # Lines must referenced the bank suspense account and the AR outstanding receipts account
        bank_statement_line = self.filtered(lambda line: line.account_id.code == BANK_SUSPENSE_ACCOUNT_CODE)
        payment_line  = self.filtered(lambda line: line.account_id.code == OUTSTANDING_RECEIPTS_ACCOUNT_CODE)
        if not bank_statement_line:
            raise UserError("Uno de los apuntes contables no hace referencia la cuenta transitoria de banco")

        if not payment_line:
            raise UserError("Uno de los apuntes contables no hace referencia a la cuenta transitoria de cobros")

        if bank_statement_line.reconciled and payment_line.reconciled:
            raise UserError('Ambas lineas se encuentran conciliadas.')
        
        # Must balance to 0
        if bank_statement_line.balance + payment_line.balance != 0:
            raise UserError("Los balances de los apuntes no coinciden")

        amount = abs(bank_statement_line.balance)

        # Since the reconciliation between the payment and bank statemet must be done
        # through an intermediate entry, use the Misc journal for that.
        misc_journal = self.env['account.journal'].search(
                [('type', '=', 'general'), 
                ('code', '=', 'MISC')]
        )

        if not misc_journal:
            raise MissingError('No se encontro un diario miscelaneo. Crear uno.')

        ref = f"CONCILIACION {bank_statement_line.move_id.ref} - {payment_line.move_id.ref}"

        try:
            move = self.env['account.move'].create({
                'journal_id': misc_journal.id,
                'ref': ref,
                'line_ids': [
                    (0, 0, {
                        'account_id': bank_statement_line.account_id.id,
                        'debit': amount,
                        'ref': ref,
                    }),
                    (0, 0, {
                        'account_id': payment_line.account_id.id,
                        'credit': amount,
                        'ref': ref,
                    })
                ]
            })

            # Finally, post the journal and commit changes to the database
            move.action_post()
            self.env.cr.commit()

            
            # Reconcile both bank and account receivables lines.
            ar_reconcile_lines = payment_line + move.line_ids.filtered(
                    lambda line: line.account_id == payment_line.account_id
            )
            bank_reconcile_lines = bank_statement_line + move.line_ids.filtered(
                    lambda line: line.account_id == bank_statement_line.account_id
            )
            ar_reconcile_lines.reconcile()
            bank_reconcile_lines.reconcile()
        except Exception as e:
            _logger.error(e)

            # Rollback any partial chance made if any exception is encountered 
            self.env.cr.rollback()

