import threading
from django.test import TestCase, TransactionTestCase
from payouts.models import Merchant, BankAccount, LedgerEntry, Payout
from payouts.services import create_payout, get_merchant_balance


class ConcurrencyTest(TransactionTestCase):
    """
    TransactionTestCase required because we need real DB transactions
    across threads, not the default test transaction wrapper.
    """

    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="1111111111",
            ifsc_code="TEST0000001",
            account_holder_name="Test",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=100_00,
            description="Seed credit",
        )

    def test_two_payouts_same_merchant_no_overdraft(self):
        """
        Merchant has 100 INR. Two threads each try to create a 60 INR payout.
        Exactly one must succeed, the other must be rejected.
        """
        results = []
        errors = []

        def attempt_payout(key):
            try:
                result = create_payout(
                    merchant_id=self.merchant.id,
                    amount_paise=60_00,
                    bank_account_id=self.bank_account.id,
                    idempotency_key=key,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=attempt_payout, args=("key-concurrent-1",))
        t2 = threading.Thread(target=attempt_payout, args=("key-concurrent-2",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        self.assertEqual(len(results), 2)

        success_count = sum(1 for r in results if r["status_code"] == 201)
        reject_count = sum(1 for r in results if r["status_code"] == 422)

        self.assertEqual(success_count, 1, "Exactly one payout should succeed")
        self.assertEqual(reject_count, 1, "Exactly one payout should be rejected")

        pending_payouts = Payout.objects.filter(
            merchant=self.merchant,
            status=Payout.Status.PENDING,
        ).count()
        self.assertEqual(pending_payouts, 1)

        balance = get_merchant_balance(self.merchant.id)
        self.assertEqual(balance["available_balance"], 40_00)
        self.assertEqual(balance["held_balance"], 60_00)

    def test_exact_balance_payout_then_second_rejected(self):
        """
        Merchant has 100 INR. First payout takes all 100.
        Second payout for any amount must be rejected.
        """
        r1 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key="key-exact-1",
        )
        self.assertEqual(r1["status_code"], 201)

        r2 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=1,
            bank_account_id=self.bank_account.id,
            idempotency_key="key-exact-2",
        )
        self.assertEqual(r2["status_code"], 422)