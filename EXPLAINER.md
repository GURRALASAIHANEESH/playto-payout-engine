# How the Payout Engine Works

This covers the five core pieces of the system: how money is tracked, how concurrent requests are handled, how duplicate requests are caught, how state transitions are enforced, and one real bug that AI introduced.

## 1. The Ledger

There is no balance column in the database. Balance is calculated every time by querying the ledger.

The `LedgerEntry` table is append-only. Each row is either a CREDIT or a DEBIT, and `amount_paise` is always a positive integer. The entry type tells you the direction.

Here's the actual query from `services.py`:

```python
def get_merchant_balance(merchant_id):
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
```

Three DB-level aggregations. No Python-side loops.

I went with a derived balance instead of a stored one because a stored balance creates two sources of truth. The column says one thing, the ledger entries say another, and under concurrent load or crash recovery, they drift apart. With a derived balance there's nothing to drift. The ledger is the truth and the balance is just a query over it.

The `held` value is worth explaining. When a merchant requests a payout, I don't create a DEBIT right away because the money hasn't actually left yet. The payout sits in `pending` or `processing`, and `held` captures that amount so no other payout can claim the same money. A DEBIT only gets created when the payout hits `completed`. If the payout fails, no DEBIT is ever written. The hold just vanishes from the query because `failed` isn't in `[pending, processing]`.

This means failed payouts need zero cleanup. The balance fixes itself.

---

## 2. The Lock

The problem: two payout requests hit at the same time, both see ₹1,000 available, both try to create a ₹600 payout. Without locking, both succeed and the merchant is overdrawn.

I prevent this with `SELECT FOR UPDATE` on the merchant row. Here's the actual code from `services.py`:

```python
with transaction.atomic():
    merchant = (
        Merchant.objects.select_for_update().get(id=merchant_id)
    )

    balance_info = get_merchant_balance(merchant_id)
    available = balance_info["available_balance"]

    if amount_paise > available:
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
```

When PostgreSQL runs `SELECT ... FOR UPDATE`, it grabs an exclusive lock on that row. Any other transaction trying to lock the same row just waits. Not rejected, not errored, just paused until the first transaction commits or rolls back.

So what happens with two concurrent requests:
- Thread A locks the merchant row, checks balance (₹1,000), creates the ₹600 payout, commits.
- Thread B was stuck at `select_for_update()` the whole time. Now it proceeds, checks balance (₹400, because Thread A's payout is now counted in `held`), tries ₹600, gets rejected.

The thing that makes this work is that the balance check happens after the lock, inside the same atomic block. If I checked balance before acquiring the lock, both threads could see ₹1,000 before either one locks anything. That's a TOCTOU bug (time-of-check-to-time-of-use). There's no gap here between checking and acting.

I lock the Merchant row and not the Payout row because at request time the payout doesn't exist yet. The merchant row is just a stable serialization point. Different merchants lock different rows so they never block each other.

There are two concurrency tests that verify this. One fires two threads both trying ₹600 on a ₹1,000 balance. Exactly one succeeds. The other drains the exact balance and confirms the second request is rejected.

---

## 3. The Idempotency

If a client sends the same `Idempotency-Key` twice, only one payout gets created. The second request gets back the same response as the first.

Detection is at the database level. The `IdempotencyKey` model has a unique constraint on `(merchant, key)`:

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["merchant", "key"],
            name="unique_merchant_idempotency_key",
        )
    ]
```

When a request comes in, I try to INSERT an idempotency row first:

```python
try:
    with transaction.atomic():
        idem_record = IdempotencyKey.objects.create(
            merchant_id=merchant_id,
            key=idempotency_key,
        )
except IntegrityError:
    idem_record = IdempotencyKey.objects.get(
        merchant_id=merchant_id, key=idempotency_key
    )
```

If the INSERT works, this is the first request. The `response_data` field is `None` at this point because the payout hasn't been created yet.

If the INSERT fails with an `IntegrityError`, the key already exists. Then there are three cases:

```python
if idem_record.is_expired():
    idem_record.delete()
    return {"error": "Idempotency key expired.", "status_code": 410}

if idem_record.response_data is not None:
    return {"data": idem_record.response_data, "status_code": idem_record.response_status_code}

return {"error": "Request with this key is already being processed.", "status_code": 409}
```

The third case is the interesting one. `response_data` is still `None`, which means the first request claimed the key but hasn't finished yet. I return 409 and let the client decide when to retry. The alternative would be to make the second request wait for the first to finish, but that means holding a DB connection open or building some notification system. 409 is simpler.

If the first request crashes after claiming the key but before finishing:

```python
except Exception:
    idem_record.delete()
    raise
```

The key is cleaned up so the next attempt can go through fresh. No orphaned keys blocking retries.

Keys are scoped per merchant through the unique constraint. Merchant 1 and Merchant 2 can both use key `"payout-001"` without conflicting.

Keys expire after 24 hours via the `is_expired()` method on the model.

---

## 4. The State Machine

Payouts have four states: `pending`, `processing`, `completed`, `failed`.

Only three transitions are allowed. Everything else raises `InvalidTransitionError`.

The full state machine from `state_machine.py`:

```python
VALID_TRANSITIONS = {
    "pending": ["processing"],
    "processing": ["completed", "failed"],
}


def transition_or_raise(current_status, new_status):
    if not can_transition(current_status, new_status):
        raise InvalidTransitionError(
            f"Cannot transition from '{current_status}' to '{new_status}'"
        )
```

There's no entry for `completed` or `failed` as keys. So `VALID_TRANSITIONS.get("completed", [])` returns an empty list and any transition from a terminal state is rejected.

This gets called inside `transition_payout()` in `services.py`, which wraps everything in an atomic block:

```python
def transition_payout(payout_id, new_status):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        transition_or_raise(payout.status, new_status)
        payout.status = new_status

        if new_status == Payout.Status.COMPLETED:
            payout.processed_at = timezone.now()
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                entry_type=LedgerEntry.EntryType.DEBIT,
                amount_paise=payout.amount_paise,
                payout=payout,
            )

        if new_status == Payout.Status.FAILED:
            payout.processed_at = timezone.now()

        payout.save()
```

The state change and the DEBIT creation are in the same transaction. If the DEBIT insert fails, the state change rolls back too. There's no way to end up with status `completed` but no DEBIT entry, or a DEBIT entry but status still `processing`.

The `select_for_update()` on the payout row prevents two Celery workers from transitioning the same payout at the same time, which could happen if `retry_stuck_payouts` and `process_pending_payouts` both pick up the same payout in the same cycle.

I wrote 11 tests for this. Every valid transition, every invalid transition (completed to pending, failed to completed, etc.), and explicit checks that completed creates exactly one DEBIT while failed creates zero.

---

## 5. The AI Audit

When I was building the retry logic, I used AI to help generate the Celery task code. It produced something that looked right and logged the right messages, but didn't actually work.

Here's what AI wrote in `retry_single_payout`:

```python
elif result == "stuck":
    backoff_seconds = 2 ** attempt
    logger.info(
        f"Payout {payout_id} still stuck. "
        f"Attempt {attempt}/{MAX_ATTEMPTS}. "
        f"Next retry in {backoff_seconds}s."
    )
```

It calculated `backoff_seconds`, logged "Next retry in 4s", and then... the function ended. Nothing scheduled the next execution with that delay. The retry only happened when `retry_stuck_payouts` ran again on its 10-second beat schedule and found the payout still stuck past the 30-second threshold. The actual delay was always 30+ seconds regardless of what the log said.

The log message said "Next retry in 4s" but the real behavior was "next retry in 30-something seconds when the scheduler happens to notice." It looked correct in the logs unless you actually traced the flow.

I caught this during an audit where I walked through the full retry path: `retry_stuck_payouts` picks up stuck payout, calls `retry_single_payout.delay()`, task runs, bank returns stuck, backoff is calculated, logged, and discarded. Nothing passes that countdown to Celery.

The fix was to move the backoff to the scheduling side in `retry_stuck_payouts`:

```python
for payout_id, attempt_count in stuck_payouts:
    backoff_seconds = 2 ** (attempt_count + 1)
    retry_single_payout.apply_async(
        args=[payout_id],
        countdown=backoff_seconds,
    )
```

`apply_async(countdown=N)` tells the Celery broker to hold the task for N seconds before delivering it to a worker. Now the delays are actually 4s, 8s, 16s.

This matters for a payment system because retrying too fast can cause duplicate bank transfers. If you send a transfer instruction while the previous one is still being processed by the bank, you might settle twice. Backoff exists to give the upstream system breathing room. A backoff that only shows up in logs gives you zero protection.