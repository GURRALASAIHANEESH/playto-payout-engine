from django.contrib import admin
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "created_at"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "account_number", "ifsc_code"]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "entry_type", "amount_paise", "created_at"]
    list_filter = ["entry_type"]


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "amount_paise", "status", "attempt_count", "created_at"]
    list_filter = ["status"]


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ["id", "merchant", "key", "response_status_code", "created_at"]