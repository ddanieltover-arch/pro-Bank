import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'probank.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def run_tests():
    client = Client(HTTP_HOST='127.0.0.1')
    try:
        user = User.objects.get(username='johndoe')
        if not hasattr(user, 'profile'):
            from accounts.models import UserProfile
            UserProfile.objects.create(user=user)
        print(f"User {user.username} found.")
    except User.DoesNotExist:
        print("User johndoe not found.")
        return

    client.force_login(user)
    
    urls = [
        '/dashboard/',
        '/dashboard/accounts/',
        '/dashboard/refunds/',
        '/dashboard/refunds/request/',
        '/dashboard/settings/',
    ]
    
    all_passed = True
    for url in urls:
        response = client.get(url)
        print(f"GET {url} -> Status: {response.status_code}")
        if response.status_code != 200:
            all_passed = False
            print(f"  Error accessing {url}. Check logs.")
    
    if all_passed:
        print("All dashboard pages rendered successfully!")
    else:
        print("Some pages failed to render.")

if __name__ == '__main__':
    run_tests()
