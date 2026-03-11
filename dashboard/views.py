from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
from .models import BankAccount, Transaction, RefundRequest
from .forms import RefundRequestForm
from accounts.forms import UserForm, UserProfileForm

@login_required
def overview(request):
    accounts = BankAccount.objects.filter(user=request.user)
    primary_account = accounts.first()
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # Get recent transactions across all accounts
    recent_transactions = Transaction.objects.filter(
        account__user=request.user
    ).order_by('-date')[:5]
    
    # Get pending refunds count and total
    pending_refunds = RefundRequest.objects.filter(user=request.user, status='pending')
    pending_count = pending_refunds.count()
    pending_total = pending_refunds.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Refund Breakdown (simplified for UI)
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
        'routing_number': '123456789', # Standard placeholder
    }
    return render(request, 'dashboard/overview.html', context)

@login_required
def accounts_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    # For simplicity, we'll show transactions for the first account or all
    transactions = Transaction.objects.filter(account__user=request.user).order_by('-date')
    
    context = {
        'active_page': 'accounts',
        'accounts': accounts,
        'transactions': transactions,
        'total_balance': total_balance,
    }
    return render(request, 'dashboard/accounts.html', context)

@login_required
def refunds(request):
    refund_requests = RefundRequest.objects.filter(user=request.user).order_by('-created_at')
    
    # Stats for the refunds page
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
def settings_view(request):
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()
        
        profile.bio = request.POST.get('bio', profile.bio)
        profile.email_notifications = 'email_notifications' in request.POST
        profile.push_notifications = 'push_notifications' in request.POST
        
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
            
        profile.save()
        messages.success(request, 'Settings saved successfully.')
        return redirect('dashboard:settings')
            
    context = {
        'active_page': 'settings',
    }
    return render(request, 'dashboard/settings.html', context)

@login_required
def add_account(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type', 'checking')
        name = f"{account_type.title()} Account"
        # Generate random account number
        import random
        acc_num = "".join([str(random.randint(0, 9)) for _ in range(12)])
        
        BankAccount.objects.create(
            user=request.user,
            name=name,
            account_type=account_type,
            account_number=acc_num,
            balance=0.00
        )
        messages.success(request, f'New {account_type} account created successfully!')
        return redirect('dashboard:accounts')
    return redirect('dashboard:accounts')

@login_required
def request_refund(request):
    if request.method == 'POST':
        form = RefundRequestForm(request.POST, request.FILES)
        if form.is_valid():
            refund = form.save(commit=False)
            refund.user = request.user
            refund.save()
            messages.success(request, f'Refund request for Order {refund.order_id} has been submitted.')
            return redirect('dashboard:refunds')
    else:
        form = RefundRequestForm()
        
    context = {
        'active_page': 'refunds',
        'form': form,
    }
    return render(request, 'dashboard/request_refund.html', context)

@login_required
def cards_view(request):
    # For now, we'll reuse recent transactions as placeholder for card activity
    card_transactions = Transaction.objects.filter(
        account__user=request.user,
        amount__lt=0
    ).order_by('-date')[:5]
    
    context = {
        'active_page': 'cards',
        'card_transactions': card_transactions,
    }
    return render(request, 'dashboard/cards.html', context)

@login_required
def transfer_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    if request.method == 'POST':
        from_account_id = request.POST.get('from_account')
        to_account_id = request.POST.get('to_account')
        amount = request.POST.get('amount')
        
        try:
            from_account = BankAccount.objects.get(id=from_account_id, user=request.user)
            amount_dec = Decimal(amount)
            
            if from_account.balance >= amount_dec:
                from_account.balance -= amount_dec
                from_account.save()
                
                # Create transaction
                Transaction.objects.create(
                    account=from_account,
                    description=f"Transfer to {to_account_id}",
                    amount=-amount_dec,
                    category="Transfer",
                    status="success"
                )
                
                # If internal transfer
                try:
                    to_account = BankAccount.objects.get(id=to_account_id, user=request.user)
                    to_account.balance += amount_dec
                    to_account.save()
                    Transaction.objects.create(
                        account=to_account,
                        description=f"Transfer from {from_account.account_number}",
                        amount=amount_dec,
                        category="Transfer",
                        status="success"
                    )
                except:
                    # External transfer simulation
                    pass
                    
                messages.success(request, f"Successfully transferred ${amount_dec}!")
                return redirect('dashboard:transfer_history')
            else:
                messages.error(request, "Insufficient funds.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {
        'active_page': 'transfer',
        'accounts': accounts,
    }
    return render(request, 'dashboard/transfer.html', context)

@login_required
def transfer_history_view(request):
    transfers = Transaction.objects.filter(
        account__user=request.user,
        description__icontains='Transfer'
    ).order_by('-date')
    context = {
        'active_page': 'transfers',
        'transfers': transfers,
    }
    return render(request, 'dashboard/transfer_history.html', context)

@login_required
def withdraw_view(request):
    accounts = BankAccount.objects.filter(user=request.user)
    if request.method == 'POST':
        account_id = request.POST.get('account')
        amount = request.POST.get('amount')
        
        try:
            account = BankAccount.objects.get(id=account_id, user=request.user)
            amount_dec = Decimal(amount)
            
            if account.balance >= amount_dec:
                account.balance -= amount_dec
                account.save()
                
                Transaction.objects.create(
                    account=account,
                    description="Withdrawal",
                    amount=-amount_dec,
                    category="Withdrawal",
                    status="success"
                )
                
                messages.success(request, f"Withdrawal of ${amount_dec} initiated successfully!")
                return redirect('dashboard:withdrawal_history')
            else:
                messages.error(request, "Insufficient funds.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    context = {
        'active_page': 'withdraw',
        'accounts': accounts,
    }
    return render(request, 'dashboard/withdraw.html', context)

import csv
from django.http import HttpResponse

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
def withdrawal_history_view(request):
    withdrawals = Transaction.objects.filter(
        account__user=request.user,
        description__icontains='Withdraw'
    ).order_by('-date')
    context = {
        'active_page': 'withdrawals',
        'withdrawals': withdrawals,
    }
    return render(request, 'dashboard/withdrawal_history.html', context)
