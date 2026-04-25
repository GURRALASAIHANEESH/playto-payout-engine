from django.test import TestCase
from unittest.mock import patch

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout
from payouts.services import get_merchant_balance, transition_payout
from payouts.tasks import retry_single_payout, MAX_ATTEMPTS


class RetryLogicTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Retry Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="1111111111",
            ifsc_code="SBIN0001234",
            account_holder_name="Retry Tester",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=500000,
            description="Seed",
        )

    def _create_processing_payout(self, amount=10000, attempts=0):
        payout = Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=amount,
            status=Payout.Status.PROCESSING,
            attempt_count=attempts,
        )
        return payout

    @patch("payouts.tasks.simulate_bank_response", return_value="completed")
    def test_retry_completes_payout(self, mock_bank):
        """Retry succeeds → payout completed, debit created."""
        payout = self._create_processing_payout(20000, attempts=1)
        retry_single_payout(payout.id)

        payout.refresh_from_db()
        self.assertEqual(payout.status, "completed")

        debit = LedgerEntry.objects.filter(
            payout=payout,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).first()
        self.assertIsNotNone(debit)
        self.assertEqual(debit.amount_paise, 20000)

    @patch("payouts.tasks.simulate_bank_response", return_value="failed")
    def test_retry_fails_payout(self, mock_bank):
        """Retry fails → payout failed, no debit."""
        payout = self._create_processing_payout(20000, attempts=1)
        retry_single_payout(payout.id)

        payout.refresh_from_db()
        self.assertEqual(payout.status, "failed")

        debit_count = LedgerEntry.objects.filter(
            payout=payout,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).count()
        self.assertEqual(debit_count, 0)

    @patch("payouts.tasks.simulate_bank_response", return_value="stuck")
    def test_max_retries_then_fail(self, mock_bank):
        """After MAX_ATTEMPTS, payout must be marked failed."""
        payout = self._create_processing_payout(30000, attempts=MAX_ATTEMPTS)
        retry_single_payout(payout.id)

        payout.refresh_from_db()
        self.assertEqual(payout.status, "failed")
        self.assertIsNotNone(payout.processed_at)

    @patch("payouts.tasks.simulate_bank_response", return_value="stuck")
    def test_max_retries_releases_hold(self, mock_bank):
        """After max retries fail, held balance returns to available."""
        payout = self._create_processing_payout(30000, attempts=MAX_ATTEMPTS)

        bal_before = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal_before["held_balance"], 30000)

        retry_single_payout(payout.id)

        bal_after = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal_after["held_balance"], 0)
        self.assertEqual(
            bal_after["available_balance"],
            bal_before["available_balance"] + 30000,
        )

    @patch("payouts.tasks.simulate_bank_response", return_value="stuck")
    def test_attempt_count_increments(self, mock_bank):
        """Each retry increments attempt_count."""
        payout = self._create_processing_payout(10000, attempts=1)
        retry_single_payout(payout.id)

        payout.refresh_from_db()
        self.assertEqual(payout.attempt_count, 2)

    def test_skips_non_processing_payout(self):
        """Retry should skip payout that is no longer processing."""
        payout = self._create_processing_payout(10000, attempts=1)
        transition_payout(payout.id, "completed")

        retry_single_payout(payout.id)

        payout.refresh_from_db()
        self.assertEqual(payout.status, "completed")