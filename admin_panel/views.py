from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal

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
        messages.success(request, f"Refund {refund.order_id} approved and balance updated.")
    else:
        refund.status = 'rejected'
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
    
    if action == 'approve':
        target_user.profile.kyc_status = 'verified'
        target_user.profile.is_verified = True
        
        # Auto-issue account if not exists
        if not BankAccount.objects.filter(user=target_user).exists():
            import random
            from decimal import Decimal
            acc_num = "".join([str(random.randint(0, 9)) for _ in range(12)])
            BankAccount.objects.create(
                user=target_user,
                name="Checking Account",
                account_type='checking',
                account_number=acc_num,
                balance=Decimal("0.00")
            )
            messages.success(request, f"KYC approved and Checking Account issued for {target_user.username}.")
        else:
            messages.success(request, f"KYC for {target_user.username} approved.")
    else:
        target_user.profile.kyc_status = 'unverified'
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
    
    if action == 'approve':
        withdrawal.status = 'success'
        withdrawal.save()
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
    
    if action == 'approve':
        card.status = 'active'
        messages.success(request, f"{card.card_type.title()} card approved.")
    else:
        card.status = 'declined'
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
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_panel:dashboard')
        else:
            messages.error(request, 'Invalid credentials or non-staff account.')
            
    return render(request, 'admin_panel/login.html')
