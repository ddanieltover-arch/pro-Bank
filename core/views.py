from django.shortcuts import render, redirect
from django.contrib import messages


def home(request):
    return render(request, 'core/index.html')


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        # In production, send email or save to database
        messages.success(request, f'Thank you {name}! Your message has been sent.')
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

