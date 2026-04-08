import os
import django
import sys

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'probank.settings')
django.setup()

from accounts.email_utils import send_html_email, notify_admin
from django.contrib.auth.models import User
from django.utils import timezone

def test_emails():
    # Attempt to get or create a test user
    test_user, created = User.objects.get_or_create(
        username='test_user_email',
        defaults={
            'email': 'refunds@my-probank.com', # Sending to the same address for testing
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    print("Testing Welcome Email...")
    welcome_success = send_html_email(
        "Welcome to ProBank!",
        'emails/welcome.html',
        {
            'user': test_user,
            'login_url': 'http://127.0.0.1:8000/accounts/login/'
        },
        [test_user.email]
    )
    print(f"Welcome Email Status: {'SUCCESS' if welcome_success else 'FAILED'}")

    print("\nTesting Transaction Notification...")
    tx_success = send_html_email(
        "Transaction Update",
        'emails/transaction_user.html',
        {
            'title': 'Withdrawal Success',
            'message_text': 'Your funds have been successfully transferred to your external bank account.',
            'reference_id': 'TX-TEST-999',
            'amount': '1,250.00',
            'currency': '$',
            'status': 'Completed',
            'date': timezone.now().strftime("%b %d, %Y %H:%M"),
            'is_negative': True,
            'dashboard_url': 'http://127.0.0.1:8000/dashboard/'
        },
        [test_user.email]
    )
    print(f"Transaction Email Status: {'SUCCESS' if tx_success else 'FAILED'}")

    print("\nTesting Admin Notification...")
    admin_success = notify_admin(
        "Test System Alert",
        "This is a test alert from the automated messaging system.",
        "Details: System is running normally. Test connection established."
    )
    print(f"Admin Email Status: {'SUCCESS' if admin_success else 'FAILED'}")

if __name__ == "__main__":
    test_emails()
