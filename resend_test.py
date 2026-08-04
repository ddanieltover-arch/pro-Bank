"""
Send a test email through Resend.

Usage:
  set RESEND_API_KEY=re_xxxx
  set DEFAULT_FROM_EMAIL=ProBank <onboarding@resend.dev>
  python resend_test.py
"""
import os
import sys

import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'probank.settings')
django.setup()

from django.conf import settings
from accounts.email_utils import send_html_email, notify_admin


def main():
    if not settings.RESEND_API_KEY:
        print('ERROR: RESEND_API_KEY is not set in the environment / .env')
        sys.exit(1)

    to = os.environ.get('TEST_EMAIL') or settings.ADMIN_NOTIFICATION_EMAIL
    print(f'From: {settings.DEFAULT_FROM_EMAIL}')
    print(f'To:   {to}')
    print('Sending test notification via Resend...')

    ok = send_html_email(
        subject='ProBank Resend test',
        template_name='emails/generic_notification.html',
        context={
            'title': 'Resend is configured',
            'message_text': 'If you received this, ProBank email delivery via Resend is working.',
            'status': 'OK',
        },
        recipient_list=[to],
    )
    print(f'send_html_email: {"queued" if ok else "FAILED"}')

    notify_admin(
        subject='Resend admin test',
        message_text='Admin notification channel test via Resend.',
        details='Triggered by resend_test.py',
    )
    print('notify_admin: queued')
    print('Check your inbox (and Resend dashboard) in a few seconds.')


if __name__ == '__main__':
    main()
