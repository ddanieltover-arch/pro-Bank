from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum
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
    context = {
        'total_users': User.objects.count(),
        'pending_refunds': RefundRequest.objects.filter(status='pending').count(),
        'total_processed': Transaction.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0,
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
    return render(request, 'admin_panel/user_detail.html', {'target_user': target_user})

@staff_member_required
def adjust_balance(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        account = BankAccount.objects.filter(user=target_user).first()
        if account:
            account.balance += amount
            account.save()
            Transaction.objects.create(
                account=account,
                description="Admin Adjustment",
                amount=amount,
                category="Adjustment",
                status="success"
            )
            messages.success(request, f"Balance adjusted for {target_user.username}")
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
    pending_kyc = User.objects.filter(profile__kyc_status='pending')
    return render(request, 'admin_panel/kyc_list.html', {'pending_kyc': pending_kyc})

@staff_member_required
def kyc_action(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    action = request.POST.get('action') # 'approve' or 'reject'
    
    if action == 'approve':
        target_user.profile.kyc_status = 'verified'
        target_user.profile.is_verified = True
        messages.success(request, f"KYC for {target_user.username} approved.")
    else:
        target_user.profile.kyc_status = 'unverified'
        messages.warning(request, f"KYC for {target_user.username} rejected.")
    
    target_user.profile.save()
    return redirect('admin_panel:kyc_list')

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
    transactions_list = Transaction.objects.all().order_by('-timestamp')[:50]
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
