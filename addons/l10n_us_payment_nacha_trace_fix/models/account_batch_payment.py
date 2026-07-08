# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import ValidationError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _generate_nacha_file(self):
        journal = self.journal_id
        header = self._generate_nacha_header()
        entries = []
        batch_nr = 0

        offset_payments = self.env["account.payment"]
        for date, payments in sorted(self.payment_ids.grouped("date").items()):
            entries.append(self._generate_nacha_batch_header_record(date, batch_nr))

            # --- PATCH: start trace number at 1 instead of 0 ---
            for payment_nr, payment in enumerate(payments, start=1):
                self._validate_bank_for_nacha(payment)
                entries.append(self._generate_nacha_entry_detail(payment_nr, payment, is_offset=False))

            offset_payment = self.env["account.payment"]
            if journal.nacha_is_balanced:
                if not journal.bank_account_id:
                    raise ValidationError(_(
                        "Please set a bank account on the %s journal.",
                        journal.display_name,
                    ))

                offset_payment = self.env["account.payment"].new({
                    "partner_id": journal.company_id.partner_id.id,
                    "partner_bank_id": journal.bank_account_id.id,
                    "amount": sum(payment.amount for payment in payments),
                    "memo": "OFFSET",
                })
                self._validate_bank_for_nacha(offset_payment)
                offset_payments |= offset_payment
                # --- PATCH: offset trace number also shifted by +1 ---
                entries.append(self._generate_nacha_entry_detail(
                    len(payments) + 1, offset_payment, is_offset=True,
                ))

            entries.append(self._generate_nacha_batch_control_record(
                payments, offset_payment, batch_nr,
            ))
            batch_nr += 1

        entries.append(self._generate_nacha_file_control_record(
            batch_nr, self.payment_ids, offset_payments,
        ))
        entries.extend(self._generate_padding(
            batch_nr, len(self.payment_ids | offset_payments),
        ))

        return "\r\n".join([header] + entries)
