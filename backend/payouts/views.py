from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Merchant, LedgerEntry, Payout
from .serializers import (
    PayoutRequestSerializer,
    PayoutSerializer,
    LedgerEntrySerializer,
    BalanceSerializer,
)
from .services import create_payout, get_merchant_balance


def get_merchant_or_error(request):
    merchant_id = request.headers.get("X-Merchant-ID")
    if not merchant_id:
        return None, Response(
            {"error": "X-Merchant-ID header required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        merchant = Merchant.objects.get(id=merchant_id)
        return merchant, None
    except Merchant.DoesNotExist:
        return None, Response(
            {"error": "Merchant not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


class MerchantBalanceView(APIView):
    def get(self, request, merchant_id):
        try:
            Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {"error": "Merchant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        balance = get_merchant_balance(merchant_id)
        return Response(BalanceSerializer(balance).data)


class MerchantLedgerView(APIView):
    def get(self, request, merchant_id):
        try:
            Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {"error": "Merchant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        entries = LedgerEntry.objects.filter(merchant_id=merchant_id)[:50]
        return Response(LedgerEntrySerializer(entries, many=True).data)


class MerchantPayoutsView(APIView):
    def get(self, request, merchant_id):
        try:
            Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response(
                {"error": "Merchant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        payouts = Payout.objects.filter(merchant_id=merchant_id)[:50]
        return Response(PayoutSerializer(payouts, many=True).data)


class PayoutCreateView(APIView):
    def post(self, request):
        merchant, error = get_merchant_or_error(request)
        if error:
            return error

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PayoutRequestSerializer(
            data=request.data,
            context={"merchant_id": merchant.id},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        result = create_payout(
            merchant_id=merchant.id,
            amount_paise=serializer.validated_data["amount_paise"],
            bank_account_id=serializer.validated_data["bank_account_id"],
            idempotency_key=idempotency_key,
        )

        response_status = result["status_code"]
        response_data = result.get("data") or {"error": result.get("error")}
        return Response(response_data, status=response_status)


class PayoutDetailView(APIView):
    def get(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except Payout.DoesNotExist:
            return Response(
                {"error": "Payout not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PayoutSerializer(payout).data)