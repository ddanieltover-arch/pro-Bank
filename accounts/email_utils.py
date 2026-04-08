from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import threading

logger = logging.getLogger(__name__)

class EmailThread(threading.Thread):
    def __init__(self, subject, text_content, html_content, from_email, recipient_list):
        self.subject = subject
        self.text_content = text_content
        self.html_content = html_content
        self.from_email = from_email
        self.recipient_list = recipient_list
        threading.Thread.__init__(self)

    def run(self):
        try:
            email = EmailMultiAlternatives(
                self.subject,
                self.text_content,
                self.from_email,
                self.recipient_list
            )
            email.attach_alternative(self.html_content, "text/html")
            email.send()
            logger.info(f"Background email sent: {self.subject} to {self.recipient_list}")
        except Exception as e:
            import sys
            sys.stderr.write(f"ASYNC EMAIL ERROR: Failed to send email '{self.subject}': {str(e)}\n")
            logger.error(f"Async email failed: {str(e)}")

def send_html_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Helper function to send branded HTML emails in the background.
    """
    if not recipient_list:
        return
        
    if not from_email:
        from_email = settings.DEFAULT_FROM_EMAIL
        
    try:
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        # Start a background thread
        EmailThread(subject, text_content, html_content, from_email, recipient_list).start()
        return True
    except Exception as e:
        import sys
        sys.stderr.write(f"EMAIL PREP ERROR: Failed to prepare email '{subject}': {str(e)}\n")
        logger.error(f"Email prep failed: {str(e)}")
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
