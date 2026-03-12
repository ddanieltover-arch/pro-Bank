from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.admin_login, name='login'),
    path('users/', views.users, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/adjust/', views.adjust_balance, name='adjust_balance'),
    path('refunds/', views.refunds, name='refunds'),
    path('refunds/<int:refund_id>/action/', views.refund_action, name='refund_action'),
    path('kyc/', views.kyc_list, name='kyc_list'),
    path('kyc/<int:user_id>/action/', views.kyc_action, name='kyc_action'),
    path('cards/', views.card_list, name='card_list'),
    path('cards/<int:card_id>/action/', views.card_action, name='card_action'),
    path('transactions/', views.transactions, name='transactions'),
    path('logs/', views.system_logs, name='system_logs'),
    path('settings/', views.settings, name='settings'),
    path('settings/password/', views.change_password, name='change_password'),
    path('suspended/', views.suspended, name='suspended'),
]
