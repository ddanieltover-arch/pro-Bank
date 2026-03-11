from django.db import models
from django.contrib.auth.models import User

class SystemLog(models.Model):
    ACTION_CHOICES = (
        ('add_funds', 'Added Funds'),
        ('withdraw_funds', 'Withdrawn Funds'),
        ('suspend_account', 'Suspended Account'),
        ('activate_account', 'Activated Account'),
        ('approve_refund', 'Approved Refund'),
        ('reject_refund', 'Rejected Refund'),
    )
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_actions')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_actions')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin} - {self.action} on {self.target_user}"
