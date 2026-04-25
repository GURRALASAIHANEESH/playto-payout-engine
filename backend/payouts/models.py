from django.db import models
from django.utils import timezone


class Merchant(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="bank_accounts"
    )
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_holder_name} - {self.account_number}"


class LedgerEntry(models.Model):
    """
    Append-only ledger. Source of truth for actual money movement.
    CREDIT = money in (e.g. payment received)
    DEBIT  = money out (created only when payout reaches 'completed')
    """

    class EntryType(models.TextChoices):
        CREDIT = "CREDIT"
        DEBIT = "DEBIT"

    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=6, choices=EntryType.choices)
    amount_paise = models.BigIntegerField()  # always positive
    description = models.CharField(max_length=255, blank=True, default="")
    # optional FK to payout for traceability on debits
    payout = models.ForeignKey(
        "Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "entry_type"]),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.amount_paise}p - {self.merchant}"


class Payout(models.Model):
    """
    Payouts in 'pending' or 'processing' status represent held funds.
    On 'completed': a DEBIT LedgerEntry is created.
    On 'failed': no debit, hold simply disappears.
    """

    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="payouts"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="payouts"
    )
    amount_paise = models.BigIntegerField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    attempt_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["status", "updated_at"]),
        ]

    def __str__(self):
        return f"Payout {self.id} - {self.amount_paise}p - {self.status}"


class IdempotencyKey(models.Model):
    """
    Scoped per merchant. Unique constraint prevents duplicate creation
    even under concurrent requests.

    Lifecycle:
    1. INSERT with response_data=None (request in flight)
    2. UPDATE with response_data + status_code once payout created
    3. Second request hitting unique constraint → look up existing row
       - If response_data exists → return cached response
       - If response_data is None → first request still in flight → return 409
    """

    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="idempotency_keys"
    )
    key = models.CharField(max_length=255)
    response_data = models.JSONField(null=True, blank=True)
    response_status_code = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "key"],
                name="unique_merchant_idempotency_key",
            )
        ]
        indexes = [
            models.Index(fields=["created_at"]),  # for 24hr expiry cleanup
        ]

    def is_expired(self):
        expiry = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() > expiry

    def __str__(self):
        return f"IKey {self.key} - merchant {self.merchant_id}"