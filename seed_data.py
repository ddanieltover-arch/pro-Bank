import os
import django
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'probank.settings')
django.setup()

from django.contrib.auth.models import User
from dashboard.models import BankAccount, Transaction, RefundRequest

def seed():
    # Get or create test user
    user, created = User.objects.get_or_create(username='johndoe')
    if created:
        user.set_password('TestPass123!')
        user.first_name = 'John'
        user.last_name = 'Doe'
        user.email = 'john@probank.com'
        user.save()

    # Create Bank Accounts
    Account_Data = [
        ('Checking Account', 'checking', '4422', 128430.00),
        ('Savings Account', 'savings', '8811', 45250.50),
        ('Investment Portfolio', 'investment', '1109', 92400.00),
    ]
    
    accounts = []
    for name, ac_type, last_four, bal in Account_Data:
        acc, _ = BankAccount.objects.get_or_create(
            user=user,
            name=name,
            account_type=ac_type,
            account_number=f"GB29PBANK00000000{last_four}",
            defaults={'balance': Decimal(bal)}
        )
        accounts.append(acc)

    # Create Transactions for the main account
    main_acc = accounts[0]
    if not main_acc.transactions.exists():
        Transaction_List = [
            ('Stripe Payout', 12400.00, 'Income', 'success'),
            ('Amazon Refund #042', -149.99, 'Shopping', 'success'),
            ('Apple Services', -9.99, 'Sub', 'success'),
            ('Freelance Payment', 2500.00, 'Income', 'pending'),
        ]
        for desc, amt, cat, status in Transaction_List:
            Transaction.objects.create(
                account=main_acc,
                description=desc,
                amount=Decimal(amt),
                category=cat,
                status=status,
                date=timezone.now() - timedelta(days=random.randint(0, 10))
            )

    # Create Refund Requests
    if not user.refund_requests.exists():
        Refund_List = [
            ('#ORD-99231', 124.50, 'defective', 'pending'),
            ('#ORD-99452', 89.00, 'wrong_item', 'approved'),
            ('#ORD-99108', 450.00, 'unauthorized', 'disputed'),
        ]
        for oid, amt, reason, status in Refund_List:
            RefundRequest.objects.create(
                user=user,
                order_id=oid,
                amount=Decimal(amt),
                reason=reason,
                status=status
            )
    print("Seed data created successfully.")

if __name__ == '__main__':
    seed()
