from rest_framework import serializers
from .models import Merchant, BankAccount, LedgerEntry, Payout


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ["id", "name", "created_at"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["id", "account_number", "ifsc_code", "account_holder_name"]


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            "id", "entry_type", "amount_paise",
            "description", "payout", "created_at",
        ]


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id", "merchant", "bank_account", "amount_paise",
            "status", "attempt_count", "created_at",
            "updated_at", "processed_at",
        ]


class PayoutRequestSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.IntegerField()

    def validate_bank_account_id(self, value):
        merchant_id = self.context.get("merchant_id")
        if not BankAccount.objects.filter(id=value, merchant_id=merchant_id).exists():
            raise serializers.ValidationError(
                "Bank account not found for this merchant."
            )
        return value


class BalanceSerializer(serializers.Serializer):
    total_credits = serializers.IntegerField()
    total_debits = serializers.IntegerField()
    held_balance = serializers.IntegerField()
    available_balance = serializers.IntegerField()