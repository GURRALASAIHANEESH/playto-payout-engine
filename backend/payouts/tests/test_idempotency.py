from django.test import TransactionTestCase
from payouts.models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
from payouts.services import create_payout


class IdempotencyTest(TransactionTestCase):

    def setUp(self):
        self.merchant = Merchant.objects.create(name="Test Merchant")
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number="2222222222",
            ifsc_code="TEST0000002",
            account_holder_name="Test",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=500_00,
            description="Seed credit",
        )

    def test_same_key_returns_same_response(self):
        key = "idem-test-001"

        r1 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key=key,
        )
        self.assertEqual(r1["status_code"], 201)

        r2 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key=key,
        )
        self.assertEqual(r2["status_code"], 201)
        self.assertEqual(r1["data"]["payout_id"], r2["data"]["payout_id"])

        payout_count = Payout.objects.filter(merchant=self.merchant).count()
        self.assertEqual(payout_count, 1, "Duplicate payout must not be created")

    def test_different_keys_create_different_payouts(self):
        r1 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key="idem-a",
        )
        r2 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key="idem-b",
        )

        self.assertEqual(r1["status_code"], 201)
        self.assertEqual(r2["status_code"], 201)
        self.assertNotEqual(r1["data"]["payout_id"], r2["data"]["payout_id"])

    def test_same_key_different_merchants_independent(self):
        merchant2 = Merchant.objects.create(name="Other Merchant")
        bank2 = BankAccount.objects.create(
            merchant=merchant2,
            account_number="3333333333",
            ifsc_code="TEST0000003",
            account_holder_name="Other",
        )
        LedgerEntry.objects.create(
            merchant=merchant2,
            entry_type=LedgerEntry.EntryType.CREDIT,
            amount_paise=500_00,
            description="Seed credit",
        )

        key = "shared-key"

        r1 = create_payout(
            merchant_id=self.merchant.id,
            amount_paise=100_00,
            bank_account_id=self.bank_account.id,
            idempotency_key=key,
        )
        r2 = create_payout(
            merchant_id=merchant2.id,
            amount_paise=100_00,
            bank_account_id=bank2.id,
            idempotency_key=key,
        )

        self.assertEqual(r1["status_code"], 201)
        self.assertEqual(r2["status_code"], 201)
        self.assertNotEqual(r1["data"]["payout_id"], r2["data"]["payout_id"])

    def test_idempotency_key_count_unchanged_on_replay(self):
        key = "idem-count-test"

        create_payout(
            merchant_id=self.merchant.id,
            amount_paise=50_00,
            bank_account_id=self.bank_account.id,
            idempotency_key=key,
        )
        create_payout(
            merchant_id=self.merchant.id,
            amount_paise=50_00,
            bank_account_id=self.bank_account.id,
            idempotency_key=key,
        )

        idem_count = IdempotencyKey.objects.filter(
            merchant=self.merchant, key=key
        ).count()
        self.assertEqual(idem_count, 1)