# backend/crypto_api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('coins/', views.CryptoListAPIView.as_view(), name='coin-list'),
    path('trigger-parsing/', views.trigger_parsing, name='trigger-parsing'),
]