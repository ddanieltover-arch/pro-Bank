from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('accounts/', views.accounts_view, name='accounts'),
    path('refunds/', views.refunds, name='refunds'),
    path('settings/', views.settings_view, name='settings'),
    path('refunds/request/', views.request_refund, name='request_refund'),
    path('cards/', views.cards_view, name='cards'),
    path('transfer/', views.transfer_view, name='transfer'),
    path('transfers/', views.transfer_history_view, name='transfer_history'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    path('withdrawals/', views.withdrawal_history_view, name='withdrawal_history'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('export/', views.export_transactions, name='export_transactions'),
]
