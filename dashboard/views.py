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
        messages.info(request, "Identity documents submitted for verification.")
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
        messages.success(request, f"New {card_type} card requested. Awaiting administrator approval.")
        return redirect('dashboard:cards')
    return redirect('dashboard:cards')

@login_required
def overview(request):
    accounts = BankAccount.objects.filter(user=request.user)
    # Ensure checking account exists
    if not accounts.filter(account_type='checking').exists() and not request.user.is_staff:
        acc_num = "".join([str(random.randint(0, 9)) for _ in range(12)])
        BankAccount.objects.create(
            user=request.user,
            name="Checking Account",
            account_type='checking',
            account_number=acc_num,
            balance=Decimal("0.00")
        )
    
    primary_account = accounts.filter(account_type='checking').first()
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
                f"Amount: {request.user.profile.currency_symbol}{amount}\nReason: {reason}\nDetails: {details}"
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
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        if 'change_password' in request.POST:
            from django.contrib.auth.forms import PasswordChangeForm
            from django.contrib.auth import update_session_auth_hash
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated.')
            else:
                messages.error(request, 'Error updating password.')
        else:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.save()
            
            profile.bio = request.POST.get('bio', profile.bio)
            if 'avatar' in request.FILES:
                profile.avatar = request.FILES['avatar']
            profile.save()
            messages.success(request, 'Profile updated.')
        return redirect('dashboard:settings')
            
    return render(request, 'dashboard/settings.html', {'active_page': 'settings'})

@login_required
@kyc_required
def withdraw_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    primary_account = accounts.first()
    if request.method == 'POST':
        amount = request.POST.get('amount')
        dest_bank = request.POST.get('destination_bank')
        dest_acc = request.POST.get('destination_account')
        
        try:
            account = primary_account # Defaulting to primary for simplified UI
            amount_dec = Decimal(amount)
            
            if account.balance >= amount_dec:
                account.balance -= amount_dec
                account.save()
                
                Transaction.objects.create(
                    account=account,
                    description=f"Withdrawal to {dest_bank}",
                    amount=-amount_dec,
                    category="Withdrawal",
                    status="pending", # Start as pending
                    destination_bank=dest_bank,
                    destination_account=dest_acc
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
                        'dashboard_url': request.build_absolute_uri(reverse('dashboard:withdrawal_history'))
                    },
                    [request.user.email]
                )
                
                # Notify Admin
                notify_admin(
                    "New Withdrawal Request",
                    f"User {request.user.username} has requested a withdrawal.",
                    f"Amount: {request.user.profile.currency_symbol}{amount_dec}\nBank: {dest_bank}\nAccount: {dest_acc}"
                )
                
                return redirect('dashboard:withdrawal_history')
            else:
                messages.error(request, "Insufficient funds.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'dashboard/withdraw.html', {'active_page': 'withdraw', 'accounts': accounts, 'primary_account': primary_account})

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
