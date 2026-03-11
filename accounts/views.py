from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:overview')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Ensure profile exists (for seeded users or edge cases)
            if not hasattr(user, 'profile'):
                from .models import UserProfile
                UserProfile.objects.get_or_create(user=user)
            login(request, user)
            next_url = request.POST.get('next', request.GET.get('next', ''))
            return redirect(next_url if next_url else 'dashboard:overview')
        else:
            form = AuthenticationForm()
            form.errors['__all__'] = ['Invalid credentials']
            return render(request, 'accounts/login.html', {'form': form})
    
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form, 'next': request.GET.get('next', '')})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:overview')
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        errors = []
        if password1 != password2:
            errors.append('Passwords do not match.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters.')
        
        if errors:
            return render(request, 'accounts/signup.html', {
                'errors': errors,
                'form_data': request.POST,
            })
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )
        login(request, user)
        messages.success(request, 'Welcome to ProBank! Your account has been created.')
        return redirect('dashboard:overview')
    
    return render(request, 'accounts/signup.html', {'form': {}})


@login_required
def kyc_view(request):
    return render(request, 'accounts/kyc.html')


@login_required
def verification_success_view(request):
    return render(request, 'accounts/verification_success.html')


def logout_view(request):
    logout(request)
    return redirect('core:home')
