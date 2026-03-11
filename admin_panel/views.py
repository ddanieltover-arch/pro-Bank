from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from dashboard.models import BankAccount, Transaction, RefundRequest
from .models import SystemLog
from django.db.models import Sum
from decimal import Decimal

@staff_member_required
def dashboard(request):
    context = {
        'total_users': User.objects.count(),
        'pending_refunds': RefundRequest.objects.filter(status='pending').count(),
        'total_processed': Transaction.objects.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0,
        'active_disputes': RefundRequest.objects.filter(status='disputed').count(),
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
    accounts = target_user.accounts.all()
    recent_transactions = Transaction.objects.filter(account__user=target_user).order_by('-date')[:10]
    return render(request, 'admin_panel/user_detail.html', {
        'target_user': target_user,
        'accounts': accounts,
        'recent_transactions': recent_transactions
    })

@staff_member_required
def adjust_balance(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        account_id = request.POST.get('account_id')
        amount = float(request.POST.get('amount', 0))
        action = request.POST.get('action') # 'add' or 'withdraw'
        
        account = get_object_or_404(BankAccount, id=account_id, user=target_user)
        
        if action == 'add':
            account.balance += (Decimal(amount) if isinstance(amount, float) else amount)
            msg = f"Added ${amount} to {account.name}"
            log_action = 'add_funds'
        else:
            account.balance -= (Decimal(amount) if isinstance(amount, float) else amount)
            msg = f"Withdrawn ${amount} from {account.name}"
            log_action = 'withdraw_funds'
            
        account.save()
        
        # Log the action
        SystemLog.objects.create(
            admin=request.user,
            target_user=target_user,
            action=log_action,
            details=f"{msg} (New Balance: ${account.balance})"
        )
        
        messages.success(request, msg)
        return redirect('admin_panel:user_detail', user_id=user_id)
    return redirect('admin_panel:users')

@staff_member_required
def refunds(request):
    refund_list = RefundRequest.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/refunds.html', {'refund_list': refund_list})

@staff_member_required
def transactions(request):
    txn_list = Transaction.objects.all().order_by('-date')
    return render(request, 'admin_panel/transactions.html', {'txn_list': txn_list})

@staff_member_required
def settings(request):
    return render(request, 'admin_panel/settings.html')

@staff_member_required
def suspended(request):
    return render(request, 'admin_panel/account_suspended.html')

@staff_member_required
def system_logs(request):
    logs = SystemLog.objects.all().order_by('-timestamp')
    return render(request, 'admin_panel/system_logs.html', {'logs': logs})
