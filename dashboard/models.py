import random

from django.db import models
from django.contrib.auth.models import User

class BankAccount(models.Model):
    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='checking')
    account_number = models.CharField(max_length=20, unique=True)
    sort_code = models.CharField(max_length=8, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (***{self.account_number[-4:]})"

    @classmethod
    def generate_unique_account_number(cls, country='USA'):
        length = 8 if country == 'UK' else 12
        while True:
            number = ''.join(str(random.randint(0, 9)) for _ in range(length))
            if not cls.objects.filter(account_number=number).exists():
                return number

    @classmethod
    def generate_sort_code(cls):
        """UK sort code in XX-XX-XX format."""
        return '-'.join(f'{random.randint(0, 99):02d}' for _ in range(3))

    @classmethod
    def create_for_user(cls, user, name='Checking Account', account_type='checking', balance=None):
        from decimal import Decimal
        country = getattr(getattr(user, 'profile', None), 'country', 'USA')
        return cls.objects.create(
            user=user,
            name=name,
            account_type=account_type,
            account_number=cls.generate_unique_account_number(country),
            sort_code=cls.generate_sort_code() if country == 'UK' else '',
            balance=balance if balance is not None else Decimal('0.00'),
        )

    def ensure_uk_details(self):
        """Backfill UK account number / sort code for existing accounts."""
        country = getattr(getattr(self.user, 'profile', None), 'country', '')
        if country != 'UK':
            return False
        updated_fields = []
        if len(self.account_number) != 8 or not self.account_number.isdigit():
            self.account_number = self.generate_unique_account_number('UK')
            updated_fields.append('account_number')
        if not self.sort_code:
            self.sort_code = self.generate_sort_code()
            updated_fields.append('sort_code')
        if updated_fields:
            self.save(update_fields=updated_fields)
            return True
        return False

class BankCard(models.Model):
    CARD_TYPES = (
        ('virtual', 'Virtual'),
        ('physical', 'Physical'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('declined', 'Declined'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    card_type = models.CharField(max_length=10, choices=CARD_TYPES, default='virtual')
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.CharField(max_length=5) # MM/YY
    cvv = models.CharField(max_length=3)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_type.title()} Card - {self.status}"

class Transaction(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    )
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    # Withdrawal details
    destination_bank = models.CharField(max_length=100, blank=True)
    destination_account = models.CharField(max_length=50, blank=True)
    destination_account_name = models.CharField(max_length=150, blank=True)
    destination_sort_code = models.CharField(max_length=8, blank=True)
    destination_reference = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"

class RefundRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('disputed', 'Disputed'),
        ('rejected', 'Rejected'),
    )
    REASON_CHOICES = (
        ('defective', 'Defective Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_delivered', 'Order Not Delivered'),
        ('duplicate', 'Duplicate Charge'),
        ('unauthorized', 'Unauthorized Transaction'),
        ('other', 'Other'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refund_requests')
    order_id = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    proof_file = models.FileField(upload_to='refund_proofs/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund {self.order_id} - {self.amount}"
