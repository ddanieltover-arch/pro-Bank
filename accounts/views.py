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
        phone_number = request.POST.get('phone_number', '')
        country = request.POST.get('country', 'USA')
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
            from .models import UserProfile
            return render(request, 'accounts/signup.html', {
                'errors': errors,
                'form_data': request.POST,
                'countries': UserProfile.COUNTRY_CHOICES
            })
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )
        # Update phone number and country in profile
        user.profile.phone_number = phone_number
        user.profile.country = country
        user.profile.save()
        
        # Send Welcome Email
        from .email_utils import send_html_email
        from django.urls import reverse
        email_sent = send_html_email(
            f"Welcome to ProBank, {user.first_name}!",
            'emails/welcome.html',
            {
                'user': user,
                'login_url': request.build_absolute_uri(reverse('accounts:login'))
            },
            [user.email]
        )
        
        login(request, user)
        if email_sent:
            messages.success(request, f'Welcome to ProBank! Your account has been created, and your confirmation email is on its way to {user.email}.')
        else:
            messages.warning(request, f'Welcome! Your account is ready, but we had trouble preparing the confirmation email. Please contact support if you don\'t receive it soon.')
        return redirect('dashboard:overview')
    
    from .models import UserProfile
    context = {
        'form': {},
        'form_data': {},
        'countries': getattr(UserProfile, 'COUNTRY_CHOICES', [('Other', 'Other (USD, $)')])
    }
    return render(request, 'accounts/signup.html', context)


@login_required
def kyc_view(request):
    if request.method == 'POST':
        profile = request.user.profile
        id_type = request.POST.get('id_type')
        id_front = request.FILES.get('id_front')
        id_back = request.FILES.get('id_back')
        
        if id_type:
            profile.id_type = id_type
        if id_front:
            profile.id_front = id_front
        if id_back:
            profile.id_back = id_back
            
        profile.kyc_status = 'pending'
        profile.save()
        
        messages.success(request, 'Documents uploaded successfully! We will review them shortly.')
        return redirect('accounts:verification_success')
        
    return render(request, 'accounts/kyc.html')


@login_required
def verification_success_view(request):
    return render(request, 'accounts/verification_success.html')


def logout_view(request):
    logout(request)
    return redirect('core:home')
