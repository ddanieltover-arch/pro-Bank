from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('careers/', views.careers, name='careers'),
    path('business-cards/', views.business_cards, name='business_cards'),
    path('global-banking/', views.global_banking, name='global_banking'),
    path('refund-engine/', views.refund_engine, name='refund_engine'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('security/', views.security, name='security'),
]
