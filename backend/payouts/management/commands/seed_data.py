from django.core.management.base import BaseCommand
from payouts.models import Merchant, BankAccount, LedgerEntry


class Command(BaseCommand):
    help = "Seed merchants with bank accounts and credit history"

    def handle(self, *args, **options):
        merchants_data = [
            {
                "name": "Acme Freelancers",
                "credits": [50000_00, 30000_00, 20000_00],
                "account": {
                    "account_number": "1234567890",
                    "ifsc_code": "HDFC0001234",
                    "account_holder_name": "Acme Freelancers Pvt Ltd",
                },
            },
            {
                "name": "DesignStudio India",
                "credits": [75000_00, 25000_00],
                "account": {
                    "account_number": "9876543210",
                    "ifsc_code": "ICIC0005678",
                    "account_holder_name": "DesignStudio India LLP",
                },
            },
            {
                "name": "CodeCraft Agency",
                "credits": [100000_00, 45000_00, 15000_00],
                "account": {
                    "account_number": "5556667778",
                    "ifsc_code": "SBIN0009012",
                    "account_holder_name": "CodeCraft Agency",
                },
            },
        ]

        for data in merchants_data:
            merchant, created = Merchant.objects.get_or_create(name=data["name"])
            action = "Created" if created else "Already exists"
            self.stdout.write(f"{action}: {merchant.name}")

            BankAccount.objects.get_or_create(
                merchant=merchant,
                account_number=data["account"]["account_number"],
                defaults={
                    "ifsc_code": data["account"]["ifsc_code"],
                    "account_holder_name": data["account"]["account_holder_name"],
                },
            )

            if created:
                for amount in data["credits"]:
                    LedgerEntry.objects.create(
                        merchant=merchant,
                        entry_type=LedgerEntry.EntryType.CREDIT,
                        amount_paise=amount,
                        description="Payment received",
                    )
                total = sum(data["credits"])
                self.stdout.write(
                    f"  Seeded {len(data['credits'])} credits, "
                    f"total: {total // 100} INR"
                )

        self.stdout.write(self.style.SUCCESS("Seeding complete."))