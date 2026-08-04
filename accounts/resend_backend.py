"""
Django email backend that sends mail through the Resend HTTP API.
"""
import logging

import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Drop-in replacement for SMTP that uses Resend."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        api_key = getattr(settings, 'RESEND_API_KEY', '') or ''
        if api_key:
            resend.api_key = api_key

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'RESEND_API_KEY', '') or ''
        if not api_key:
            logger.error('RESEND_API_KEY is not configured; cannot send email.')
            if not self.fail_silently:
                raise RuntimeError('RESEND_API_KEY is not configured.')
            return 0

        resend.api_key = api_key
        sent_count = 0

        for message in email_messages:
            try:
                self._send(message)
                sent_count += 1
            except Exception as exc:
                logger.error('Resend email failed: %s', exc)
                if not self.fail_silently:
                    raise

        return sent_count

    def _send(self, message):
        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        to = list(message.to or [])
        if not to:
            return

        params = {
            'from': from_email,
            'to': to,
            'subject': message.subject or '',
        }

        if message.cc:
            params['cc'] = list(message.cc)
        if message.bcc:
            params['bcc'] = list(message.bcc)
        if message.reply_to:
            params['reply_to'] = list(message.reply_to)

        html_body = None
        text_body = message.body or ''

        for content, mimetype in getattr(message, 'alternatives', []) or []:
            if mimetype == 'text/html':
                html_body = content
                break

        if html_body:
            params['html'] = html_body
            if text_body:
                params['text'] = text_body
        else:
            params['text'] = text_body or ' '

        import base64

        attachments = []
        for attachment in getattr(message, 'attachments', []) or []:
            if isinstance(attachment, tuple) and len(attachment) >= 2:
                filename, content = attachment[0], attachment[1]
                if isinstance(content, str):
                    content = content.encode('utf-8')
                attachments.append({
                    'filename': filename,
                    'content': base64.b64encode(content).decode('ascii'),
                })
        if attachments:
            params['attachments'] = attachments

        resend.Emails.send(params)
        logger.info('Resend email sent: %s → %s', message.subject, to)
