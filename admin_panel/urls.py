from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/adjust/', views.adjust_balance, name='adjust_balance'),
    path('refunds/', views.refunds, name='refunds'),
    path('transactions/', views.transactions, name='transactions'),
    path('logs/', views.system_logs, name='system_logs'),
    path('settings/', views.settings, name='settings'),
    path('suspended/', views.suspended, name='suspended'),
]
