from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    KYC_STATUS = (
        ('unverified', 'Unverified'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
    )
    ACCOUNT_TIERS = (
        ('basic', 'Basic'),
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('premium', 'Premium'),
    )
    ID_TYPES = (
        ('national_id', 'National ID Card'),
        ('passport', 'Passport'),
        ('drivers_license', 'Driver\'s License'),
        ('resident_permit', 'Resident Permit'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS, default='unverified')
    account_level = models.CharField(max_length=20, choices=ACCOUNT_TIERS, default='basic')
    id_type = models.CharField(max_length=20, choices=ID_TYPES, blank=True)
    id_front = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    id_back = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
