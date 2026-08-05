from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from dashboard.models import BankAccount, Transaction, RefundRequest, BankCard
from .models import SystemLog

def staff_member_required(view_func=None):
    actual_decorator = user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='admin_panel:login'
    )
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator

@staff_member_required
def dashboard(request):
    # Group processed totals by currency
    currency_totals = []
    try:
        processed_by_country = Transaction.objects.filter(status='success').values('account__user__profile__country').annotate(total=Sum('amount'))
        
        # Map country to symbol
        from accounts.models import UserProfile
        symbol_map = {
            'UK': '£', 'DE': '€', 'FR': '€', 'IT': '€', 'ES': '€',
            'JP': '¥', 'CN': '¥', 'IN': '₹', 'BR': 'R$', 'KR': '₩',
            'CH': 'CHF', 'ID': 'Rp', 'SA': '﷼', 'USA': '$', 'Canada': '$', 'AU': '$', 'MX': '$', 'SG': '$', 'NZ': '$', 'AR': '$', 'Other': '$'
        }
        
        for item in processed_by_country:
            country = item['account__user__profile__country']
            symbol = symbol_map.get(country, '$')
            # Check if symbol already in list to aggregate (e.g. multiple countries using $)
            found = False
            for ct in currency_totals:
                if ct['symbol'] == symbol:
                    ct['total'] += item['total']
                    found = True
                    break
            if not found:
                currency_totals.append({'symbol': symbol, 'total': item['total']})
    except Exception as e:
        # Fallback if field is missing (unapplied migration)
        currency_totals = [{'symbol': '$', 'total': Transaction.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0}]

    context = {
        'total_users': User.objects.count(),
        'pending_refunds': RefundRequest.objects.filter(status='pending').count(),
        'currency_totals': currency_totals,
        'active_disputes': RefundRequest.objects.filter(status='disputed').count(),
        'pending_kyc': User.objects.filter(profile__kyc_status='pending').count(),
        'pending_cards': BankCard.objects.filter(status='pending').count(),
        'recent_refunds': RefundRequest.objects.all().order_by('-created_at')[:5],
        'recent_logs': SystemLog.objects.all().order_by('-timestamp')[:10],
    }
    return render(request, 'admin_panel/dashboard.html', context)

@staff_member_required
def users(request):
    users_list = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_panel/users.html', {'users_list': users_list})

@staff_member_required
def user_detail(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    accounts = BankAccount.objects.filter(user=target_user)
    recent_transactions = Transaction.objects.filter(account__in=accounts).order_by('-date')[:10]
    
    context = {
        'target_user': target_user,
        'accounts': accounts,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'admin_panel/user_detail.html', context)

@staff_member_required
def adjust_balance(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        amount_str = request.POST.get('amount', '0')
        account_id = request.POST.get('account_id')
        
        try:
            amount = Decimal(amount_str)
            if action == 'withdraw':
                amount = -amount

            if account_id:
                account = BankAccount.objects.get(id=account_id, user=target_user)
            else:
                account = BankAccount.objects.filter(user=target_user).first()

            if account:
                account.balance += amount
                account.save()
                
                Transaction.objects.create(
                    account=account,
                    description=f"Admin {action.title()} Adjustment",
                    amount=amount,
                    category="Adjustment",
                    status="success"
                )
                
                # Log action
                SystemLog.objects.create(
                    admin=request.user,
                    target_user=target_user,
                    action=f'{action}_funds',
                    details=f"Admin {request.user.username} {action}ed {target_user.profile.currency_symbol}{abs(amount)}."
                )
                
                messages.success(request, f"Balance adjusted for {target_user.username}")
        except Exception as e:
            messages.error(request, f"Error adjusting balance: {str(e)}")
            
    return redirect('admin_panel:user_detail', user_id=user_id)

@staff_member_required
def refunds(request):
    refunds_list = RefundRequest.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/refunds.html', {'refunds_list': refunds_list})

@staff_member_required
def refund_action(request, refund_id):
    refund = get_object_or_404(RefundRequest, id=refund_id)
    action = request.POST.get('action') # 'approve' or 'reject'
    
    from accounts.email_utils import send_html_email
    from django.urls import reverse
    
    if action == 'approve':
        refund.status = 'approved'
        # Add funds to user's primary account
        account = BankAccount.objects.filter(user=refund.user).first()
        if account:
            account.balance += refund.amount
            account.save()
            Transaction.objects.create(
                account=account,
                description=f"Refund Approved: {refund.order_id}",
                amount=refund.amount,
                category="Refund",
                status="success"
            )
            
            # Notify User
            send_html_email(
                f"Refund Approved: {refund.order_id}",
                'emails/transaction_user.html',
                {
                    'title': 'Refund Successful',
                    'message_text': f'Your refund request for Order #{refund.order_id} has been approved and the funds have been credited to your account.',
                    'reference_id': f'REF-{refund.order_id}',
                    'amount': f'{refund.amount:,.2f}',
                    'currency': refund.user.profile.currency_symbol,
                    'status': 'Completed',
                    'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                    'is_negative': False,
                    'dashboard_url': request.build_absolute_uri(reverse('dashboard:refunds'))
                },
                [refund.user.email]
            )
            
        messages.success(request, f"Refund {refund.order_id} approved and balance updated.")
    else:
        refund.status = 'rejected'
        
        # Notify User
        send_html_email(
            f"Refund Request Update: {refund.order_id}",
            'emails/generic_notification.html',
            {
                'title': 'Refund Request Rejected',
                'message_text': f'Your refund request for Order #{refund.order_id} has been reviewed and unfortunately could not be approved at this time. Please contact support for more details.',
                'action_url': request.build_absolute_uri(reverse('dashboard:refunds')),
                'action_text': 'View Refund Status'
            },
            [refund.user.email]
        )
        
        messages.warning(request, f"Refund {refund.order_id} rejected.")
    
    refund.save()
    return redirect('admin_panel:refunds')

@staff_member_required
def kyc_list(request):
    status = request.GET.get('status', 'pending')
    kyc_requests = User.objects.filter(profile__kyc_status=status)
    return render(request, 'admin_panel/kyc_list.html', {
        'kyc_requests': kyc_requests,
        'current_status': status
    })

@staff_member_required
def kyc_action(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    action = request.POST.get('action') # 'approve' or 'reject'
    
    from accounts.email_utils import send_html_email
    from django.urls import reverse

    if action == 'approve':
        target_user.profile.kyc_status = 'verified'
        target_user.profile.is_verified = True
        
        # Auto-issue account if not exists
        if not BankAccount.objects.filter(user=target_user).exists():
            BankAccount.create_for_user(target_user)
            
        # Notify User
        send_html_email(
            "KYC Verification Successful",
            'emails/generic_notification.html',
            {
                'title': 'Verification Approved',
                'message_text': 'Congratulations! Your identity documents have been verified. You now have full access to all banking features, including withdrawals and card requests.',
                'action_url': request.build_absolute_uri(reverse('dashboard:overview')),
                'action_text': 'Go to Dashboard'
            },
            [target_user.email]
        )
        messages.success(request, f"KYC approved and account verified for {target_user.username}.")
    else:
        target_user.profile.kyc_status = 'unverified'
        
        # Notify User
        send_html_email(
            "KYC Verification Update",
            'emails/generic_notification.html',
            {
                'title': 'Verification Rejected',
                'message_text': 'Unfortunately, your identity verification could not be completed. This may be due to unclear document photos or mismatched information. Please re-upload your documents for another review.',
                'action_url': request.build_absolute_uri(reverse('dashboard:overview')),
                'action_text': 'Re-upload Documents'
            },
            [target_user.email]
        )
        messages.warning(request, f"KYC for {target_user.username} rejected.")
    
    target_user.profile.save()
    return redirect('admin_panel:kyc_list')

@staff_member_required
def withdrawal_list(request):
    status = request.GET.get('status', 'pending')
    withdrawals = Transaction.objects.filter(
        category='Withdrawal', 
        status=status
    ).order_by('-date')
    return render(request, 'admin_panel/withdraw_list.html', {
        'withdrawals': withdrawals,
        'current_status': status
    })

@staff_member_required
def withdrawal_action(request, tx_id):
    withdrawal = get_object_or_404(Transaction, id=tx_id, category='Withdrawal')
    action = request.POST.get('action') # 'approve' or 'reject'
    
    from accounts.email_utils import send_html_email
    from django.urls import reverse

    if action == 'approve':
        withdrawal.status = 'success'
        withdrawal.save()
        
        # Notify User
        send_html_email(
            "Withdrawal Successful",
            'emails/transaction_user.html',
            {
                'title': 'Withdrawal Completed',
                'message_text': f'Your withdrawal request to {withdrawal.destination_bank} has been approved and processed. The funds should appear in your destination account shortly.',
                'reference_id': f'TX-{withdrawal.id}',
                'amount': f'{abs(withdrawal.amount):,.2f}',
                'currency': withdrawal.account.user.profile.currency_symbol,
                'status': 'Completed',
                'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                'is_negative': True,
                'dashboard_url': request.build_absolute_uri(reverse('dashboard:withdrawal_history'))
            },
            [withdrawal.account.user.email]
        )
        
        messages.success(request, f"Withdrawal request for {withdrawal.account.user.username} approved.")
    elif action == 'reject':
        withdrawal.status = 'failed'
        withdrawal.save()
        
        # Refund the amount back to the user
        account = withdrawal.account
        account.balance += abs(withdrawal.amount)
        account.save()
        
        # Create a refund transaction entry
        Transaction.objects.create(
            account=account,
            description=f"Rejected Withdrawal Refund: {withdrawal.id}",
            amount=abs(withdrawal.amount),
            category="Refund",
            status="success"
        )
        
        # Notify User
        send_html_email(
            "Withdrawal Request Update",
            'emails/transaction_user.html',
            {
                'title': 'Withdrawal Rejected',
                'message_text': f'Your withdrawal request to {withdrawal.destination_bank} was rejected. The funds have been returned to your ProBank balance.',
                'reference_id': f'TX-{withdrawal.id}',
                'amount': f'{abs(withdrawal.amount):,.2f}',
                'currency': withdrawal.account.user.profile.currency_symbol,
                'status': 'Rejected',
                'date': timezone.now().strftime("%b %d, %Y %H:%M"),
                'is_negative': False,
                'dashboard_url': request.build_absolute_uri(reverse('dashboard:withdrawal_history'))
            },
            [withdrawal.account.user.email]
        )
        
        SystemLog.objects.create(
            admin=request.user,
            target_user=account.user,
            action='reject_refund', # Reusing action for logging
            details=f"Admin {request.user.username} rejected withdrawal {withdrawal.id} and refunded {account.user.profile.currency_symbol}{abs(withdrawal.amount)}."
        )
        messages.warning(request, f"Withdrawal request rejected. Funds returned to {account.user.username}.")
    
    return redirect('admin_panel:withdrawal_list')

@staff_member_required
def card_list(request):
    pending_cards = BankCard.objects.filter(status='pending')
    return render(request, 'admin_panel/card_list.html', {'pending_cards': pending_cards})

@staff_member_required
def card_action(request, card_id):
    card = get_object_or_404(BankCard, id=card_id)
    action = request.POST.get('action') # 'approve' or 'reject'
    
    from accounts.email_utils import send_html_email
    from django.urls import reverse

    if action == 'approve':
        card.status = 'active'
        
        # Notify User
        send_html_email(
            "Bank Card Approved",
            'emails/generic_notification.html',
            {
                'title': 'Card Issued Successfully',
                'message_text': f'Your request for a {card.card_type} bank card has been approved. Your new card (ending in {card.card_number[-4:]}) is now active and ready for use.',
                'action_url': request.build_absolute_uri(reverse('dashboard:cards')),
                'action_text': 'View My Cards'
            },
            [card.user.email]
        )
        messages.success(request, f"{card.card_type.title()} card approved.")
    else:
        card.status = 'declined'
        
        # Notify User
        send_html_email(
            "Bank Card Request Update",
            'emails/generic_notification.html',
            {
                'title': 'Card Request Declined',
                'message_text': f'Your request for a {card.card_type} bank card was unfortunately declined. Please ensure your account has sufficient verification and contact support if you believe this is an error.',
                'action_url': request.build_absolute_uri(reverse('dashboard:cards')),
                'action_text': 'View My Cards'
            },
            [card.user.email]
        )
        messages.warning(request, f"{card.card_type.title()} card rejected.")
    
    card.save()
    return redirect('admin_panel:card_list')

@staff_member_required
def transactions(request):
    transactions_list = Transaction.objects.all().order_by('-date')[:50]
    return render(request, 'admin_panel/transactions.html', {'transactions_list': transactions_list})

@staff_member_required
def system_logs(request):
    logs = SystemLog.objects.all().order_by('-timestamp')[:100]
    return render(request, 'admin_panel/system_logs.html', {'logs': logs})

@staff_member_required
def settings(request):
    return render(request, 'admin_panel/settings.html', {'user': request.user})

@staff_member_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('admin_panel:settings')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'admin_panel/settings.html', {'form': form})

@staff_member_required
def suspended(request):
    suspended_users = User.objects.filter(is_active=False)
    return render(request, 'admin_panel/suspended.html', {'suspended_users': suspended_users})

def admin_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or 'admin_panel:dashboard'
    # Default to named url if it matches the fallback, otherwise treat as path
    if next_url == 'admin_panel:dashboard':
        from django.urls import reverse
        next_url = reverse('admin_panel:dashboard')
        
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(next_url)
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials or non-staff account.')
            
    return render(request, 'admin_panel/login.html', {'next': request.GET.get('next', '')})

from django.core.management import call_command
from django.http import HttpResponse

def run_migrations(request):
    """Temporary utility to run migrations from browser for serverless environments."""
    token = request.GET.get('token')
    if token != 'probank-init':
        return HttpResponse("<h1>Unauthorized</h1><p>You must provide the setup token.</p>", status=403)
        
    try:
        call_command('migrate', interactive=False)
        message = "<h1>Migration Successful!</h1><p>The database schema is now up to date.</p>"
        
        # Create Admin Account Automatically
        try:
            from django.contrib.auth.models import User
            username = 'proadmin'
            email = 'admin@probank.com'
            password = 'admin123'
            
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username, email, password)
                message += f"<p><strong>Admin created successfully.</strong><br>Username: {username}<br>Password: {password}</p>"
            else:
                message += f"<p>Admin account '{username}' already exists.</p>"
        except Exception as admin_err:
            message += f"<p>Warning: Failed to create admin account: {str(admin_err)}</p>"
            
        message += "<a href='/admin-panel/'>Return to Dashboard Login</a>"
        return HttpResponse(message)
    except Exception as e:
        return HttpResponse(f"<h1>Migration Failed</h1><pre>{str(e)}</pre>")
