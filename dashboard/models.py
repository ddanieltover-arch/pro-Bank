from django.db import models
from django.contrib.auth.models import User

class BankAccount(models.Model):
    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('investment', 'Investment'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='checking')
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (***{self.account_number[-4:]})"

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
