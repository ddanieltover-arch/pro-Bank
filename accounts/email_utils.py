from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_html_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Helper function to send branded HTML emails.
    """
    if not recipient_list:
        return
        
    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL
        
    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            recipient_list
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        logger.info(f"Email sent: {subject} to {recipient_list}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def notify_admin(subject, message_text, details=None):
    """
    Quick helper to notify admin about system events.
    """
    context = {
        'message_text': message_text,
        'details': details,
        'is_admin': True,
    }
    # Using a list of admins from settings if available, otherwise fallback
    admin_emails = [email for name, email in getattr(settings, 'ADMINS', [('Admin', 'refunds@my-probank.com')])]
    
    return send_html_email(
        f"[ADMIN] {subject}",
        'emails/transaction_admin.html',
        context,
        admin_emails
    )
