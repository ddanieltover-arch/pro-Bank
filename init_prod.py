import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'probank.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin():
    username = 'proadmin'
    email = 'admin@probank.com'
    password = 'admin123'
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Superuser '{username}' created successfully.")
    else:
        print(f"Superuser '{username}' already exists.")

if __name__ == "__main__":
    create_admin()
