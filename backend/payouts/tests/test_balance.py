from django.test import TestCase

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout
from payouts.services import get_merchant_balance, transition_payout


class BalanceCalculationTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Balance Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="9876543210",
            ifsc_code="ICIC0005678",
            account_holder_name="Balance Tester",
        )

    def _credit(self, amount):
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=amount,
            description="Test credit",
        )

    def test_empty_balance(self):
        """No entries → all zeros."""
        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["total_credits"], 0)
        self.assertEqual(bal["total_debits"], 0)
        self.assertEqual(bal["held_balance"], 0)
        self.assertEqual(bal["available_balance"], 0)

    def test_credits_only(self):
        """Credits with no payouts → full available."""
        self._credit(50000)
        self._credit(30000)
        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["total_credits"], 80000)
        self.assertEqual(bal["available_balance"], 80000)
        self.assertEqual(bal["held_balance"], 0)

    def test_pending_payout_reduces_available(self):
        """Pending payout should reduce available but show as held."""
        self._credit(100000)
        Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=40000,
            status=Payout.Status.PENDING,
        )
        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["available_balance"], 60000)
        self.assertEqual(bal["held_balance"], 40000)

    def test_processing_payout_reduces_available(self):
        """Processing payout should also reduce available."""
        self._credit(100000)
        Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=25000,
            status=Payout.Status.PROCESSING,
        )
        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["available_balance"], 75000)
        self.assertEqual(bal["held_balance"], 25000)

    def test_completed_payout_debit_reflected(self):
        """After completion: debit created, hold released, available correct."""
        self._credit(100000)
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=30000,
            status=Payout.Status.PENDING,
        )
        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "completed")

        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["total_credits"], 100000)
        self.assertEqual(bal["total_debits"], 30000)
        self.assertEqual(bal["held_balance"], 0)
        self.assertEqual(bal["available_balance"], 70000)

    def test_failed_payout_releases_hold(self):
        """After failure: no debit, hold released, full balance restored."""
        self._credit(100000)
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=30000,
            status=Payout.Status.PENDING,
        )

        bal_during = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal_during["available_balance"], 70000)
        self.assertEqual(bal_during["held_balance"], 30000)

        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "failed")

        bal_after = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal_after["total_debits"], 0)
        self.assertEqual(bal_after["held_balance"], 0)
        self.assertEqual(bal_after["available_balance"], 100000)

    def test_multiple_payouts_mixed_states(self):
        """Multiple payouts in different states computed correctly."""
        self._credit(200000)

        Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=30000,
            status=Payout.Status.PENDING,
        )

        Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=20000,
            status=Payout.Status.PROCESSING,
        )

        completed_payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=50000,
            status=Payout.Status.PENDING,
        )
        transition_payout(completed_payout.id, "processing")
        transition_payout(completed_payout.id, "completed")

        failed_payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=10000,
            status=Payout.Status.PENDING,
        )
        transition_payout(failed_payout.id, "processing")
        transition_payout(failed_payout.id, "failed")

        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal["total_credits"], 200000)
        self.assertEqual(bal["total_debits"], 50000)
        self.assertEqual(bal["held_balance"], 50000)
        self.assertEqual(bal["available_balance"], 100000)