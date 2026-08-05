from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
from .models import BankAccount, Transaction, RefundRequest, BankCard
from .forms import RefundRequestForm
from accounts.forms import UserForm, UserProfileForm
from django.utils import timezone
from datetime import timedelta
import random
import csv



def kyc_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if request.user.profile.kyc_status != 'verified':
            messages.warning(request, "Please complete your KYC verification to perform this action.")
            return redirect('dashboard:overview')
        return view_func(request, *args, **kwargs)
    return _wrapped_view_func

@login_required
def kyc_upload(request):
    if request.method == 'POST':
        profile = request.user.profile
        profile.id_type = request.POST.get('id_type')
        profile.id_front = request.FILES.get('id_front')
        profile.id_back = request.FILES.get('id_back')
        profile.kyc_status = 'pending'
        profile.save()
        
        # Notify user + admin
        from accounts.email_utils import send_html_email, notify_admin
        from django.urls import reverse
        send_html_email(
            "KYC Documents Received",
            'emails/generic_notification.html',
            {
                'title': 'Identity Verification in Progress',
                'message_text': 'We have received your identity documents. Our team will review them manually and update your status within 24-48 hours.',
                'action_url': request.build_absolute_uri(reverse('dashboard:overview')),
                'action_text': 'Go to Dashboard'
            },
            [request.user.email]
        )
        notify_admin(
            "New KYC Submission",
            f"User {request.user.username} has submitted identity documents for verification.",
            (
                f"User: {request.user.get_full_name() or request.user.username} ({request.user.email})\n"
                f"ID Type: {profile.id_type or 'N/A'}\n"
                f"Status: Pending\n"
                f"Front uploaded: {'Yes' if profile.id_front else 'No'}\n"
                f"Back uploaded: {'Yes' if profile.id_back else 'No'}\n"
                f"Submitted: {timezone.now().strftime('%b %d, %Y %H:%M')}"
            ),
        )
        
        messages.info(request, "Identity documents submitted. A confirmation email is on its way.")
        return redirect('dashboard:overview')
    return render(request, 'dashboard/kyc.html', {'active_page': 'overview'})

@login_required
@kyc_required
def generate_card(request):
    if request.method == 'POST':
        card_type = request.POST.get('card_type', 'virtual')
        
        # Enforce limits: Max 1 Physical, 1 Virtual
        existing_card = BankCard.objects.filter(user=request.user, card_type=card_type).exclude(status='declined').first()
        if existing_card:
            messages.error(request, f"You already have an active or pending {card_type} card request.")
            return redirect('dashboard:cards')

        # Generate card details
        num = "".join([str(random.randint(0, 9)) for _ in range(16)])
        expiry = (timezone.now() + timedelta(days=365*5)).strftime("%m/%y")
        cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
        
        BankCard.objects.create(
            user=request.user,
            card_type=card_type,
            card_number=num,
            expiry_date=expiry,
            cvv=cvv,
            status='pending'
        )
        
        # Notify user + admin
        from accounts.email_utils import send_html_email, notify_admin
        from django.urls import reverse
        send_html_email(
            f"{card_type.title()} Card Requested",
            'emails/card_request_user.html',
            {
                'title': 'Card Request Received',
                'message_text': (
                    f'Your request for a new {card_type} bank card has been received. '
                    'You will receive another notification once it has been approved and issued.'
                ),
                'card_type': card_type.title(),
                'status': 'Pending Review',
                'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                'last_four': num[-4:],
                'action_url': request.build_absolute_uri(reverse('dashboard:cards')),
                'action_text': 'View Card Status',
            },
            [request.user.email]
        )
        notify_admin(
            "New Card Request",
            f"User {request.user.username} has requested a new {card_type} bank card.",
            (
                f"User: {request.user.get_full_name() or request.user.username} ({request.user.email})\n"
                f"Card Type: {card_type.title()}\n"
                f"Status: Pending\n"
                f"Requested: {timezone.now().strftime('%b %d, %Y %H:%M')}"
            ),
        )
        
        messages.success(request, f"New {card_type} card requested. A confirmation email is on its way.")
        return redirect('dashboard:cards')
    return redirect('dashboard:cards')

@login_required
def overview(request):
    accounts = BankAccount.objects.filter(user=request.user)
    # Ensure checking account exists
    if not accounts.filter(account_type='checking').exists() and not request.user.is_staff:
        BankAccount.create_for_user(request.user)
        accounts = BankAccount.objects.filter(user=request.user)

    primary_account = accounts.filter(account_type='checking').first()
    is_uk = getattr(request.user.profile, 'country', '') == 'UK'
    if primary_account and is_uk:
        primary_account.ensure_uk_details()

    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or Decimal("0.00")

    recent_transactions = Transaction.objects.filter(
        account__user=request.user
    ).order_by('-date')[:5]

    pending_refunds = RefundRequest.objects.filter(user=request.user, status='pending')
    pending_count = pending_refunds.count()
    pending_total = pending_refunds.aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

    all_refunds = RefundRequest.objects.filter(user=request.user)
    total_refunds_count = all_refunds.count()
    recovered_count = all_refunds.filter(status='approved').count()
    in_process_count = all_refunds.filter(status='pending').count()

    recovered_percent = 0
    in_process_percent = 0
    if total_refunds_count > 0:
        recovered_percent = int((recovered_count / total_refunds_count) * 100)
        in_process_percent = int((in_process_count / total_refunds_count) * 100)

    context = {
        'active_page': 'overview',
        'accounts': accounts,
        'primary_account': primary_account,
        'total_balance': total_balance,
        'recent_transactions': recent_transactions,
        'pending_count': pending_count,
        'pending_total': pending_total,
        'total_refunds_count': total_refunds_count,
        'recovered_count': recovered_count,
        'in_process_count': in_process_count,
        'recovered_percent': recovered_percent,
        'in_process_percent': in_process_percent,
        'routing_number': '123456789',
        'is_uk': is_uk,
        'account_holder_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'dashboard/overview.html', context)

def health_check(request):
    return HttpResponse("OK", content_type="text/plain")

@login_required
def accounts_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(account__user=request.user).order_by('-date')
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or Decimal("0.00")
    return render(request, 'dashboard/accounts.html', {
        'active_page': 'accounts',
        'accounts': accounts,
        'transactions': transactions,
        'total_balance': total_balance
    })

@login_required
def refunds(request):
    refund_requests = RefundRequest.objects.filter(user=request.user).order_by('-created_at')
    pending_count = refund_requests.filter(status='pending').count()
    approved_count = refund_requests.filter(status='approved').count()
    disputed_count = refund_requests.filter(status='disputed').count()
    
    context = {
        'active_page': 'refunds',
        'refund_requests': refund_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'disputed_count': disputed_count,
    }
    return render(request, 'dashboard/refunds.html', context)

@login_required
def request_refund(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        amount_str = request.POST.get('amount')
        reason = request.POST.get('reason')
        details = request.POST.get('description')
        proof = request.FILES.get('evidence')
        
        try:
            amount = Decimal(amount_str)

            RefundRequest.objects.create(
                user=request.user,
                order_id=order_id,
                amount=amount,
                reason=reason,
                details=details,
                proof_file=proof
            )
            messages.success(request, "Refund request submitted successfully.")
            
            # Send Email Notifications
            from accounts.email_utils import send_html_email, notify_admin
            from django.urls import reverse
            
            # Notify User
            send_html_email(
                "Refund Request Submitted",
                'emails/transaction_user.html',
                {
                    'title': 'Refund Request Received',
                    'message_text': f'Your refund request for Order #{order_id} has been received. Our team will review the evidence provided and update you shortly.',
                    'reference_id': f'REF-{order_id}',
                    'amount': f'{amount:,.2f}',
                    'currency': request.user.profile.currency_symbol,
                    'status': 'Under Review',
                    'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                    'is_negative': False,
                    'dashboard_url': request.build_absolute_uri(reverse('dashboard:refunds'))
                },
                [request.user.email]
            )
            
            # Notify Admin
            notify_admin(
                "New Refund Request",
                f"User {request.user.username} has submitted a refund request for Order #{order_id}.",
                (
                    f"User: {request.user.get_full_name() or request.user.username} ({request.user.email})\n"
                    f"Order ID: #{order_id}\n"
                    f"Amount: {request.user.profile.currency_symbol}{amount}\n"
                    f"Reason: {reason}\n"
                    f"Details: {details or 'N/A'}"
                ),
            )
            
            return redirect('dashboard:refunds')
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
            return redirect('dashboard:request_refund')
            
    context = {
        'active_page': 'refunds',
    }
    return render(request, 'dashboard/request_refund.html', context)



@login_required
def settings_view(request):
    from accounts.models import UserProfile

    user = request.user
    profile = user.profile
    active_tab = 'profile'

    if request.method == 'POST':
        if 'change_password' in request.POST:
            from django.contrib.auth.forms import PasswordChangeForm
            from django.contrib.auth import update_session_auth_hash
            form = PasswordChangeForm(user, request.POST)
            active_tab = 'security'
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated.')
                return redirect('dashboard:settings')
            else:
                for error in form.errors.values():
                    messages.error(request, error.as_text())
        else:
            user.first_name = request.POST.get('first_name', user.first_name).strip()
            user.last_name = request.POST.get('last_name', user.last_name).strip()
            user.save()

            profile.bio = request.POST.get('bio', profile.bio)
            profile.phone_number = request.POST.get('phone_number', profile.phone_number).strip()
            country = request.POST.get('country', profile.country)
            valid_countries = {code for code, _ in UserProfile.COUNTRY_CHOICES}
            if country in valid_countries:
                profile.country = country
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.save()
            messages.success(request, 'Profile updated.')
            return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html', {
        'active_page': 'settings',
        'active_tab': active_tab,
        'countries': UserProfile.COUNTRY_CHOICES,
    })


@login_required
def support_view(request):
    user = request.user
    if request.method == 'POST':
        from accounts.email_utils import notify_admin, send_html_email

        subject = (request.POST.get('subject') or 'Support request').strip()
        message_text = (request.POST.get('message') or '').strip()
        name = f"{user.first_name} {user.last_name}".strip() or user.username
        email = user.email

        if message_text:
            details = (
                f"User: {user.username} (ID: {user.id})\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message_text}"
            )
            admin_ok = notify_admin(
                subject=f"Support: {subject}",
                message_text=f"New support request from {name}",
                details=details,
                reply_to=[email] if email else None,
            )
            user_ok = False
            if email:
                user_ok = send_html_email(
                    subject="We received your support request — ProBank",
                    template_name='emails/generic_notification.html',
                    context={
                        'title': 'Support request received',
                        'message_text': (
                            f"Hi {name}, thanks for contacting ProBank Support. "
                            "Our team has received your message and will get back to you shortly."
                        ),
                        'status': 'Received',
                    },
                    recipient_list=[email],
                )
            if admin_ok or user_ok:
                messages.success(request, 'Your message has been sent. Our support team will reply soon.')
            else:
                messages.error(
                    request,
                    'We could not send your message right now. Please try WhatsApp or email refunds@my-probank.com.',
                )
        else:
            messages.error(request, 'Please enter a message before submitting.')
        return redirect('dashboard:support')

    return render(request, 'dashboard/support.html', {
        'active_page': 'support',
    })


@login_required
@kyc_required
def withdraw_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    primary_account = accounts.first()
    is_uk = getattr(request.user.profile, 'country', '') == 'UK'
    if request.method == 'POST':
        amount = request.POST.get('amount')
        dest_bank = (request.POST.get('destination_bank') or '').strip()
        dest_acc = (request.POST.get('destination_account') or '').strip()
        dest_account_name = (request.POST.get('destination_account_name') or '').strip()
        dest_sort_code = (request.POST.get('destination_sort_code') or '').strip()
        dest_reference = (request.POST.get('destination_reference') or '').strip()

        try:
            account = primary_account  # Defaulting to primary for simplified UI
            amount_dec = Decimal(amount)

            if is_uk:
                if not all([dest_account_name, dest_acc, dest_sort_code, dest_bank]):
                    messages.error(request, "Please complete all required UK bank details.")
                    return render(request, 'dashboard/withdraw.html', {
                        'active_page': 'withdraw',
                        'accounts': accounts,
                        'primary_account': primary_account,
                        'is_uk': is_uk,
                    })

            if account.balance >= amount_dec:
                account.balance -= amount_dec
                account.save()

                Transaction.objects.create(
                    account=account,
                    description=f"Withdrawal to {dest_bank}",
                    amount=-amount_dec,
                    category="Withdrawal",
                    status="pending",  # Start as pending
                    destination_bank=dest_bank,
                    destination_account=dest_acc,
                    destination_account_name=dest_account_name,
                    destination_sort_code=dest_sort_code,
                    destination_reference=dest_reference,
                )

                # Notify admin
                from admin_panel.models import SystemLog
                SystemLog.objects.create(
                    target_user=request.user,
                    action='withdraw_funds',
                    details=f"User {request.user.username} requested withdrawal of {request.user.profile.currency_symbol}{amount_dec} to {dest_bank}."
                )

                messages.success(request, f"Withdrawal request for {request.user.profile.currency_symbol}{amount_dec} submitted!")

                # Send Email Notifications
                from accounts.email_utils import send_html_email, notify_admin
                from django.urls import reverse

                # Notify User
                send_html_email(
                    "Withdrawal Request Received",
                    'emails/transaction_user.html',
                    {
                        'title': 'Withdrawal Pending',
                        'message_text': f'Your request to withdraw funds to {dest_bank} has been received and is currently pending review.',
                        'reference_id': f'WD-{random.randint(10000, 99999)}',
                        'amount': f'{amount_dec:,.2f}',
                        'currency': request.user.profile.currency_symbol,
                        'status': 'Pending',
                        'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                        'is_negative': True,
                        'transfer_fee': 'FREE',
                        'destination_bank': dest_bank,
                        'destination_account': dest_acc,
                        'destination_account_name': dest_account_name,
                        'destination_sort_code': dest_sort_code,
                        'destination_reference': dest_reference,
                        'dashboard_url': request.build_absolute_uri(reverse('dashboard:withdrawal_history'))
                    },
                    [request.user.email]
                )

                admin_lines = [
                    f"User: {request.user.get_full_name() or request.user.username} ({request.user.email})",
                    f"Amount: {request.user.profile.currency_symbol}{amount_dec}",
                    f"Transfer Fee: FREE",
                    f"Bank: {dest_bank}",
                    f"Account: {dest_acc}",
                ]
                if dest_account_name:
                    admin_lines.insert(3, f"Account Name: {dest_account_name}")
                if dest_sort_code:
                    admin_lines.append(f"Sort Code: {dest_sort_code}")
                if dest_reference:
                    admin_lines.append(f"Reference: {dest_reference}")

                # Notify Admin
                notify_admin(
                    "New Withdrawal Request",
                    f"User {request.user.username} has requested a withdrawal.",
                    "\n".join(admin_lines),
                )

                return redirect('dashboard:withdrawal_history')
            else:
                messages.error(request, "Insufficient funds.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'dashboard/withdraw.html', {
        'active_page': 'withdraw',
        'accounts': accounts,
        'primary_account': primary_account,
        'is_uk': is_uk,
    })

@login_required
def export_transactions(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="probank_transactions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Amount', 'Category', 'Status'])
    
    transactions = Transaction.objects.filter(account__user=request.user).order_by('-date')
    for tx in transactions:
        writer.writerow([tx.date, tx.description, tx.amount, tx.category, tx.status])
        
    return response

@login_required
@kyc_required
def cards_view(request):
    cards = BankCard.objects.filter(user=request.user).order_by('-created_at')
    # For now, we'll reuse recent transactions as placeholder for card activity
    card_transactions = Transaction.objects.filter(
        account__user=request.user,
        amount__lt=0
    ).order_by('-date')[:5]
    
    context = {
        'active_page': 'cards',
        'cards': cards,
        'card_transactions': card_transactions,
    }
    return render(request, 'dashboard/cards.html', context)

def health_check(request):
    """Simple endpoint for keep-alive pings."""
    return HttpResponse("OK", status=200)

@login_required
def withdrawal_history_view(request):
    withdrawals = Transaction.objects.filter(
        account__user=request.user,
        category='Withdrawal'
    ).order_by('-date')
    
    # Calculate statistics
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    month_total = withdrawals.filter(
        status='success',
        date__gte=month_start
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")
    
    pending_total = withdrawals.filter(
        status='pending'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")
    
    pending_count = withdrawals.filter(status='pending').count()
    
    ytd_volume = withdrawals.filter(
        status='success',
        date__gte=year_start
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")
    
    context = {
        'active_page': 'withdrawals',
        'withdrawals': withdrawals,
        'month_total': abs(month_total),
        'pending_total': abs(pending_total),
        'pending_count': pending_count,
        'ytd_volume': abs(ytd_volume),
    }
    return render(request, 'dashboard/withdrawal_history.html', context)
