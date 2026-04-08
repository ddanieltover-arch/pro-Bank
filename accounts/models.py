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

    ID_TYPES = (
        ('national_id', 'National ID Card'),
        ('passport', 'Passport'),
        ('drivers_license', 'Driver\'s License'),
        ('resident_permit', 'Resident Permit'),
    )
    COUNTRY_CHOICES = (
        ('USA', 'United States (USD, $)'),
        ('Canada', 'Canada (CAD, $)'),
        ('UK', 'United Kingdom (GBP, £)'),
        ('AU', 'Australia (AUD, $)'),
        ('DE', 'Germany (EUR, €)'),
        ('FR', 'France (EUR, €)'),
        ('IT', 'Italy (EUR, €)'),
        ('ES', 'Spain (EUR, €)'),
        ('JP', 'Japan (JPY, ¥)'),
        ('CN', 'China (CNY, ¥)'),
        ('IN', 'India (INR, ₹)'),
        ('BR', 'Brazil (BRL, R$)'),
        ('MX', 'Mexico (MXN, $)'),
        ('KR', 'South Korea (KRW, ₩)'),
        ('SG', 'Singapore (SGD, $)'),
        ('CH', 'Switzerland (CHF)'),
        ('NZ', 'New Zealand (NZD, $)'),
        ('AR', 'Argentina (ARS, $)'),
        ('ID', 'Indonesia (IDR, Rp)'),
        ('SA', 'Saudi Arabia (SAR, ﷼)'),
        ('Other', 'Other (USD, $)'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS, default='unverified')

    id_type = models.CharField(max_length=20, choices=ID_TYPES, blank=True)
    id_front = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    id_back = models.ImageField(upload_to='kyc_docs/', null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default='USA')

    @property
    def currency_symbol(self):
        symbols = {
            'UK': '£', 'DE': '€', 'FR': '€', 'IT': '€', 'ES': '€',
            'JP': '¥', 'CN': '¥', 'IN': '₹', 'BR': 'R$', 'KR': '₩',
            'CH': 'CHF', 'ID': 'Rp', 'SA': '﷼',
        }
        return symbols.get(self.country, '$')

    @property
    def currency_code(self):
        codes = {
            'UK': 'GBP', 'Canada': 'CAD', 'AU': 'AUD', 'DE': 'EUR', 'FR': 'EUR',
            'IT': 'EUR', 'ES': 'EUR', 'JP': 'JPY', 'CN': 'CNY', 'IN': 'INR',
            'BR': 'BRL', 'MX': 'MXN', 'KR': 'KRW', 'SG': 'SGD', 'CH': 'CHF',
            'NZ': 'NZD', 'AR': 'ARS', 'ID': 'IDR', 'SA': 'SAR', 'USA': 'USD', 'Other': 'USD'
        }
        return codes.get(self.country, 'USD')

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
