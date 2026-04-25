from django.db import transaction, IntegrityError
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Merchant, LedgerEntry, Payout, IdempotencyKey
from .state_machine import transition_or_raise, InvalidTransitionError


def get_merchant_balance(merchant_id):
    """
    Compute balance at DB level.
    available = total_credits - total_debits - total_held
    held = sum of amount_paise for payouts in pending/processing
    """
    credits = (
        LedgerEntry.objects.filter(
            merchant_id=merchant_id, entry_type=LedgerEntry.EntryType.CREDIT
        ).aggregate(total=Sum("amount_paise"))["total"]
        or 0
    )

    debits = (
        LedgerEntry.objects.filter(
            merchant_id=merchant_id, entry_type=LedgerEntry.EntryType.DEBIT
        ).aggregate(total=Sum("amount_paise"))["total"]
        or 0
    )

    held = (
        Payout.objects.filter(
            merchant_id=merchant_id,
            status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING],
        ).aggregate(total=Sum("amount_paise"))["total"]
        or 0
    )

    available = credits - debits - held
    return {
        "total_credits": credits,
        "total_debits": debits,
        "held_balance": held,
        "available_balance": available,
    }


def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key):
    """
    Create a payout with full idempotency and concurrency safety.

    Flow:
    1. Check if idempotency key exists (handle expired, in-flight, completed)
    2. Lock merchant row with SELECT FOR UPDATE
    3. Compute available balance at DB level
    4. Create payout if sufficient funds
    5. Cache response in idempotency record
    """
    # Step 1: Try to claim the idempotency key
    try:
        with transaction.atomic():
            idem_record = IdempotencyKey.objects.create(
                merchant_id=merchant_id,
                key=idempotency_key,
            )
    except IntegrityError:
        # Key already exists — check what state it's in
        idem_record = IdempotencyKey.objects.get(
            merchant_id=merchant_id, key=idempotency_key
        )

        if idem_record.is_expired():
            # Expired key — delete and reject. Caller can retry with same key.
            idem_record.delete()
            return {
                "error": "Idempotency key expired. Please retry.",
                "status_code": 410,
            }

        if idem_record.response_data is not None:
            # Already completed — return cached response
            return {
                "data": idem_record.response_data,
                "status_code": idem_record.response_status_code,
            }

        # response_data is None — first request still in flight
        return {
            "error": "A request with this idempotency key is already being processed.",
            "status_code": 409,
        }

    # Step 2-5: Lock merchant, check balance, create payout
    try:
        with transaction.atomic():
            # Lock merchant row — serializes concurrent payout requests
            merchant = (
                Merchant.objects.select_for_update().get(id=merchant_id)
            )

            # DB-level balance computation inside the lock
            balance_info = get_merchant_balance(merchant_id)
            available = balance_info["available_balance"]

            if amount_paise <= 0:
                response_data = {"error": "Amount must be positive."}
                status_code = 400
            elif amount_paise > available:
                response_data = {
                    "error": "Insufficient balance.",
                    "available_balance": available,
                    "requested_amount": amount_paise,
                }
                status_code = 422
            else:
                payout = Payout.objects.create(
                    merchant=merchant,
                    bank_account_id=bank_account_id,
                    amount_paise=amount_paise,
                    status=Payout.Status.PENDING,
                )
                response_data = {
                    "payout_id": payout.id,
                    "amount_paise": payout.amount_paise,
                    "status": payout.status,
                    "created_at": payout.created_at.isoformat(),
                }
                status_code = 201

            # Cache response in idempotency record
            idem_record.response_data = response_data
            idem_record.response_status_code = status_code
            idem_record.save(update_fields=["response_data", "response_status_code"])

        return {"data": response_data, "status_code": status_code}

    except Exception:
        # If anything fails, clean up the idempotency record so it can be retried
        idem_record.delete()
        raise


def transition_payout(payout_id, new_status):
    """
    Atomically transition a payout and handle side effects.
    - On 'completed': create a DEBIT ledger entry
    - On 'failed': no debit, hold disappears naturally
    """
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        # State machine check — raises InvalidTransitionError if illegal
        transition_or_raise(payout.status, new_status)

        payout.status = new_status
        payout.updated_at = timezone.now()

        if new_status == Payout.Status.COMPLETED:
            payout.processed_at = timezone.now()
            # Create debit atomically with state change
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT,
                amount_paise=payout.amount_paise,
                description=f"Payout #{payout.id} completed",
                payout=payout,
            )

        if new_status == Payout.Status.FAILED:
            payout.processed_at = timezone.now()
            # No debit created — hold disappears because payout is no longer pending/processing

        payout.save()

    return payout