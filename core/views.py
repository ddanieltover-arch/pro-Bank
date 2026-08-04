from django.shortcuts import render, redirect
from django.contrib import messages

from accounts.email_utils import notify_admin, send_html_email


def home(request):
    return render(request, 'core/index.html')


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        subject = (request.POST.get('subject') or 'Contact form inquiry').strip()
        message_text = (request.POST.get('message') or '').strip()

        if name and email and message_text:
            details = (
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message_text}"
            )
            admin_ok = notify_admin(
                subject=f"Contact: {subject}",
                message_text=f"New contact inquiry from {name}",
                details=details,
                reply_to=[email],
            )
            user_ok = send_html_email(
                subject="We received your message — ProBank",
                template_name='emails/generic_notification.html',
                context={
                    'title': 'Message received',
                    'message_text': (
                        f"Hi {name}, thanks for contacting ProBank. "
                        "Our team has received your message and will get back to you shortly."
                    ),
                    'status': 'Received',
                },
                recipient_list=[email],
            )
            if admin_ok or user_ok:
                messages.success(request, f'Thank you {name}! Your message has been sent.')
            else:
                messages.error(
                    request,
                    'We could not send your message right now. Please email refunds@my-probank.com directly.',
                )
        else:
            messages.error(request, 'Please fill in your name, email, and message.')
        return redirect('core:contact')
    return render(request, 'core/contact.html')


def careers(request):
    return render(request, 'core/careers.html')


def business_cards(request):
    return render(request, 'core/business_cards.html')


def global_banking(request):
    return render(request, 'core/global_banking.html')


def refund_engine(request):
    return render(request, 'core/refund_engine.html')


def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')


def terms_of_service(request):
    return render(request, 'core/terms_of_service.html')


def security(request):
    return render(request, 'core/security.html')
