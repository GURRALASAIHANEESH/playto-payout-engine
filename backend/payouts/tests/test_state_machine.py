from django.test import TestCase

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout
from payouts.services import transition_payout
from payouts.state_machine import InvalidTransitionError


class StateMachineTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="1234567890",
            ifsc_code="HDFC0001234",
            account_holder_name="Test User",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=100000,
            description="Seed",
        )

    def _create_payout(self, amount=10000):
        return Payout.objects.create(
            merchant=self.merchant,
            bank_account=self.bank_account,
            amount_paise=amount,
            status=Payout.Status.PENDING,
        )

    def test_pending_to_processing(self):
        """Valid: pending → processing."""
        payout = self._create_payout()
        result = transition_payout(payout.id, "processing")
        self.assertEqual(result.status, "processing")

    def test_processing_to_completed(self):
        """Valid: processing → completed."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        result = transition_payout(payout.id, "completed")
        self.assertEqual(result.status, "completed")

    def test_processing_to_failed(self):
        """Valid: processing → failed."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        result = transition_payout(payout.id, "failed")
        self.assertEqual(result.status, "failed")

    def test_pending_to_completed_blocked(self):
        """Illegal: pending → completed must raise."""
        payout = self._create_payout()
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "completed")

    def test_pending_to_failed_blocked(self):
        """Illegal: pending → failed must raise."""
        payout = self._create_payout()
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "failed")

    def test_completed_to_pending_blocked(self):
        """Illegal: completed → pending must raise."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "completed")
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "pending")

    def test_completed_to_failed_blocked(self):
        """Illegal: completed → failed must raise."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "completed")
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "failed")

    def test_failed_to_completed_blocked(self):
        """Illegal: failed → completed must raise."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "failed")
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "completed")

    def test_failed_to_pending_blocked(self):
        """Illegal: failed → pending must raise."""
        payout = self._create_payout()
        transition_payout(payout.id, "processing")
        transition_payout(payout.id, "failed")
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout.id, "pending")

    def test_completed_creates_debit(self):
        """Completing a payout must create exactly one DEBIT ledger entry."""
        payout = self._create_payout(5000)
        transition_payout(payout.id, "processing")

        debits_before = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).count()

        transition_payout(payout.id, "completed")

        debits_after = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).count()

        self.assertEqual(debits_after - debits_before, 1)

        debit = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
            payout=payout,
        ).first()

        self.assertIsNotNone(debit)
        self.assertEqual(debit.amount_paise, 5000)

    def test_failed_creates_no_debit(self):
        """Failing a payout must NOT create a DEBIT ledger entry."""
        payout = self._create_payout(5000)
        transition_payout(payout.id, "processing")

        debits_before = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).count()

        transition_payout(payout.id, "failed")

        debits_after = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.DEBIT,
        ).count()

        self.assertEqual(debits_after, debits_before)