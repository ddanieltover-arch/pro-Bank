from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_email_brand_context(extra=None):
    """Shared ProBank branding values for every HTML email template."""
    site_url = getattr(settings, 'SITE_URL', 'https://my-probank.com').rstrip('/')
    static_base = f'{site_url}/{settings.STATIC_URL.lstrip("/")}'
    context = {
        'site_url': site_url,
        'logo_url': f'{static_base}emails/probank-logo-white.png',
        'logo_icon_url': f'{static_base}emails/probank-icon.png',
        'support_email': getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', 'refunds@my-probank.com'),
        'privacy_url': f'{site_url}/privacy-policy/',
        'terms_url': f'{site_url}/terms-of-service/',
        'contact_url': f'{site_url}/contact/',
        'admin_url': f'{site_url}/admin-panel/',
    }
    if extra:
        context.update(extra)
    return context


def _deliver_email(subject, text_content, html_content, from_email, recipient_list, reply_to=None):
    """Send one email via the configured Django email backend (Resend)."""
    email = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        recipient_list,
        reply_to=reply_to or None,
    )
    email.attach_alternative(html_content, 'text/html')
    sent = email.send(fail_silently=False)
    logger.info('Email sent: %s → %s (count=%s)', subject, recipient_list, sent)
    return sent > 0


def send_html_email(subject, template_name, context, recipient_list, from_email=None, reply_to=None):
    """
    Send a branded HTML email via Resend.

    Sends synchronously so delivery errors surface in logs (and don't die
    silently when gunicorn recycles the worker after the HTTP response).
    """
    if not recipient_list:
        return False

    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        html_content = render_to_string(template_name, get_email_brand_context(context))
        text_content = strip_tags(html_content)
        return _deliver_email(
            subject,
            text_content,
            html_content,
            from_email,
            list(recipient_list),
            reply_to=reply_to,
        )
    except Exception as e:
        logger.exception("Failed to send email '%s' to %s: %s", subject, recipient_list, e)
        return False


def notify_admin(subject, message_text, details=None, reply_to=None):
    """
    Notify admin about system events.
    """
    context = {
        'message_text': message_text,
        'details': details,
        'is_admin': True,
    }
    admin_email = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', None)
    admin_emails = [
        email for name, email in getattr(
            settings,
            'ADMINS',
            [('Admin', admin_email)] if admin_email else [],
        )
        if email
    ]
    if not admin_emails and admin_email:
        admin_emails = [admin_email]

    if not admin_emails:
        logger.error('No ADMIN_NOTIFICATION_EMAIL / ADMINS configured; admin notify skipped.')
        return False

    return send_html_email(
        f'[ADMIN] {subject}',
        'emails/transaction_admin.html',
        context,
        admin_emails,
        reply_to=reply_to,
    )
