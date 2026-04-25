import random
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Payout
from .services import transition_payout
from .state_machine import InvalidTransitionError

logger = logging.getLogger(__name__)

STUCK_THRESHOLD_SECONDS = 30
MAX_ATTEMPTS = 3


def simulate_bank_response():
    roll = random.randint(1, 100)
    if roll <= 70:
        return "completed"
    elif roll <= 90:
        return "failed"
    else:
        return "stuck"


@shared_task(bind=True, max_retries=0)
def process_pending_payouts(self):
    pending_ids = list(
        Payout.objects.filter(status=Payout.Status.PENDING)
        .values_list("id", flat=True)
    )

    for payout_id in pending_ids:
        try:
            process_single_payout.delay(payout_id)
        except Exception:
            logger.exception(f"Failed to enqueue payout {payout_id}")


@shared_task(bind=True, max_retries=0)
def process_single_payout(self, payout_id):
    try:
        payout = transition_payout(payout_id, "processing")
    except InvalidTransitionError:
        logger.info(f"Payout {payout_id} already moved past pending, skipping.")
        return
    except Payout.DoesNotExist:
        logger.warning(f"Payout {payout_id} not found.")
        return

    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)
        payout.attempt_count += 1
        payout.save(update_fields=["attempt_count"])

    result = simulate_bank_response()

    if result == "completed":
        transition_payout(payout_id, "completed")
        logger.info(f"Payout {payout_id} completed.")

    elif result == "failed":
        transition_payout(payout_id, "failed")
        logger.info(f"Payout {payout_id} failed.")

    elif result == "stuck":
        logger.info(f"Payout {payout_id} stuck in processing. Will be retried.")


@shared_task(bind=True, max_retries=0)
def retry_stuck_payouts(self):
    cutoff = timezone.now() - timedelta(seconds=STUCK_THRESHOLD_SECONDS)

    stuck_payouts = list(
        Payout.objects.filter(
            status=Payout.Status.PROCESSING,
            updated_at__lte=cutoff,
        ).values_list("id", "attempt_count")
    )

    for payout_id, attempt_count in stuck_payouts:
        try:
            backoff_seconds = 2 ** (attempt_count + 1)
            retry_single_payout.apply_async(
                args=[payout_id],
                countdown=backoff_seconds,
            )
            logger.info(
                f"Scheduled retry for payout {payout_id} "
                f"in {backoff_seconds}s (attempt {attempt_count + 1})."
            )
        except Exception:
            logger.exception(f"Failed to enqueue retry for payout {payout_id}")


@shared_task(bind=True, max_retries=0)
def retry_single_payout(self, payout_id):
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status != Payout.Status.PROCESSING:
            logger.info(f"Payout {payout_id} no longer processing, skipping retry.")
            return

        payout.attempt_count += 1
        attempt = payout.attempt_count
        payout.save(update_fields=["attempt_count", "updated_at"])

    if attempt > MAX_ATTEMPTS:
        transition_payout(payout_id, "failed")
        logger.info(f"Payout {payout_id} failed after {MAX_ATTEMPTS} attempts.")
        return

    result = simulate_bank_response()

    if result == "completed":
        transition_payout(payout_id, "completed")
        logger.info(f"Payout {payout_id} completed on retry attempt {attempt}.")

    elif result == "failed":
        transition_payout(payout_id, "failed")
        logger.info(f"Payout {payout_id} failed on retry attempt {attempt}.")

    elif result == "stuck":
        logger.info(
            f"Payout {payout_id} still stuck. "
            f"Attempt {attempt}/{MAX_ATTEMPTS}. "
            f"Will be picked up by retry_stuck_payouts."
        )