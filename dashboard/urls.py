from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('kyc/', views.kyc_upload, name='kyc_upload'),
    path('accounts/', views.accounts_view, name='accounts'),
    path('refunds/', views.refunds, name='refunds'),
    path('settings/', views.settings_view, name='settings'),
    path('support/', views.support_view, name='support'),
    path('refunds/request/', views.request_refund, name='request_refund'),
    path('cards/', views.cards_view, name='cards'),
    path('cards/generate/', views.generate_card, name='generate_card'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    path('health/', views.health_check, name='health_check'),
    path('withdrawals/', views.withdrawal_history_view, name='withdrawal_history'),
    path('export/', views.export_transactions, name='export_transactions'),

]
